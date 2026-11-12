import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from core.tests.test_fabro_config import FABRO, read_toml
from core.tests.test_issue_triage import INPUTS, attribute

ROOT = Path(__file__).resolve().parents[2]
SPEC = FABRO / "workflows" / "spec"
AGENTS = ("propose", "sketch", "risk", "spec_fit", "fidelity", "revise")
REVIEWERS = {"risk": "risk", "spec_fit": "spec fit", "fidelity": "fidelity"}
# the issue inputs, and the three a revision run adds
SPEC_INPUTS = INPUTS + ["change_name", "feedback", "revision_scope"]
# every check step runs the default branch's copy, which install puts here
MAIN = ".intentable/main"


def graph():
    """the spec graph's text, its steps by name, and its edges as (from, to, condition)"""
    text = (SPEC / "workflow.fabro").read_text()
    body = re.sub(r"(?m)^\s*//.*$", "", text)
    steps = {
        node: attrs
        for node, attrs in re.findall(r"^\s*(\w+)\s*\[(.*?)\]\s*$", body, re.MULTILINE | re.DOTALL)
        if node != "graph"
    }
    edges = []
    for line in body.splitlines():
        if "->" not in line:
            continue
        chain, _, rest = line.partition("[")
        nodes = [n.strip() for n in chain.split("->")]
        condition = attribute(rest, "condition") if rest else None
        edges += [(a, b, condition) for a, b in zip(nodes, nodes[1:])]
    return text, steps, edges


def settings():
    return read_toml(SPEC / "workflow.toml")


def prompt(name):
    return (SPEC / f"{name}.md").read_text()


def next_steps(edges, node):
    return {(b, c) for a, b, c in edges if a == node}


class WorkflowShapeTestCase(SimpleTestCase):
    """a spec workflow exists; a proposal that needs screens includes sketches; every agent runs through ACP"""

    def test_workflow_shape(self):
        text, steps, edges = graph()
        install = attribute(steps["install"], "script")
        for pinned in (
            "@anthropic-ai/claude-code@2.1.316",
            "@agentclientprotocol/claude-agent-acp@0.99.1",
            "@fission-ai/openspec@1.16.0",
            "--branch skill-v4.8.0 https://github.com/pbakaus/impeccable",
        ):
            self.assertIn(pinned, install)
        self.assertEqual(next_steps(edges, "start"), {("install", None)})
        self.assertEqual(next_steps(edges, "install"), {("propose", None)})
        self.assertEqual(attribute(steps["propose"], "prompt"), "@propose.md")
        self.assertEqual(next_steps(edges, "propose"), {("check_draft", None)})
        self.assertEqual(
            attribute(steps["check_draft"], "script"),
            "python3 .intentable/main/check-intentable-result spec --draft",
        )
        self.assertEqual(next_steps(edges, "check_draft"), {("route", None)})
        self.assertRegex(steps["fork"], r"\bshape=component\b")
        self.assertEqual(next_steps(edges, "fork"), {(r, None) for r in REVIEWERS})
        for reviewer in REVIEWERS:
            self.assertEqual(attribute(steps[reviewer], "prompt"), f"@{reviewer}.md")
            self.assertEqual(next_steps(edges, reviewer), {("merge", None)})
        self.assertRegex(steps["merge"], r"\bshape=tripleoctagon\b")
        self.assertEqual(next_steps(edges, "merge"), {("check_reviews", None)})
        self.assertEqual(
            next_steps(edges, "check_reviews"),
            {("finish", "context.review_done=true"), ("revise", None)},
        )
        self.assertEqual(attribute(steps["revise"], "prompt"), "@revise.md")
        self.assertEqual(next_steps(edges, "revise"), {("recheck", None)})
        self.assertEqual(
            attribute(steps["recheck"], "script"),
            "python3 .intentable/main/check-intentable-result spec --draft",
        )
        self.assertEqual(next_steps(edges, "recheck"), {("fork", None)})
        self.assertEqual(
            attribute(steps["finish"], "script"),
            "python3 .intentable/main/check-intentable-result spec",
        )
        self.assertEqual(next_steps(edges, "finish"), {("exit", None)})
        self.assertEqual(settings()["workflow"]["graph"], "workflow.fabro")

    def test_check_steps_run_the_copies(self):
        text, steps, edges = graph()
        install = attribute(steps["install"], "script")
        self.assertIn("git fetch --quiet origin HEAD", install)
        for source in ("bin/check-intentable-result", "bin/check-intentable-reviews", ".fabro/workflows/spec/sketch.md"):
            name = source.rsplit("/", 1)[1]
            self.assertIn(f"git show FETCH_HEAD:{source} > {MAIN}/{name}", install)
        self.assertTrue(install.endswith(f"python3 {MAIN}/check-intentable-reviews --record-existing"))
        for name, attrs in steps.items():
            script = attribute(attrs, "script")
            if script is None or name == "install":
                continue
            self.assertRegex(script, rf"^python3 {re.escape(MAIN)}/check-intentable-(result|reviews)\b", name)

    def test_a_revision_skips_the_sketch_step(self):
        text, steps, edges = graph()
        # a revision's route, "revised", takes the unconditional edge; only "sketch" reaches the sketch agent
        self.assertIn(("fork", None), next_steps(edges, "route"))
        self.assertEqual({a for a, b, c in edges if b == "sketch"}, {"route"})
        self.assertEqual({c for a, b, c in edges if b == "sketch"}, {"context.route=sketch"})

    def test_reviewers_retry_a_sandbox_hiccup(self):
        # issue #29's spec_fit failed once on a Daytona 500 and wasn't tried again
        text, steps, edges = graph()
        for reviewer in ("risk", "spec_fit", "fidelity"):
            self.assertEqual(attribute(steps[reviewer], "max_retries"), "2", reviewer)

    def test_sketch_step_only_for_needs_design(self):
        text, steps, edges = graph()
        self.assertEqual(attribute(steps["route"], "output_schema"), "routing")
        self.assertEqual(
            next_steps(edges, "route"),
            {
                ("sketch", "context.route=sketch"),
                ("finish", "context.route=back"),
                ("fork", None),
            },
        )
        self.assertEqual(attribute(steps["sketch"], "prompt"), "@sketch.md")
        self.assertEqual(next_steps(edges, "sketch"), {("check_sketches", None)})
        self.assertEqual(
            attribute(steps["check_sketches"], "script"),
            "python3 .intentable/main/check-intentable-result spec --sketches",
        )
        self.assertEqual(next_steps(edges, "check_sketches"), {("fork", None)})
        # the revise loop never reaches the sketch step
        self.assertNotIn(
            "sketch",
            {b for a, b, c in edges if a in ("revise", "recheck", "check_reviews")},
        )

    def test_every_agent_through_acp(self):
        text, steps, edges = graph()
        agents = {name for name, attrs in steps.items() if attribute(attrs, "type") == "agent"}
        self.assertEqual(agents, set(AGENTS))
        for name in AGENTS:
            self.assertEqual(attribute(steps[name], "backend"), "acp", name)
            self.assertEqual(attribute(steps[name], "acp.command"), "claude-agent-acp", name)
        # every other step is a script or a structural node, never a prompt stage
        for name, attrs in steps.items():
            if name not in AGENTS:
                self.assertIsNone(attribute(attrs, "prompt"), name)


class WorkflowContractTestCase(SimpleTestCase):
    """the spec workflow follows the workflow contract"""

    def test_inputs_used_commands_without_inputs(self):
        self.assertEqual(settings()["run"]["inputs"], {name: "" for name in SPEC_INPUTS})
        for key in SPEC_INPUTS:
            self.assertIn(f"{{{{ inputs.{key} }}}}", prompt("propose"), key)
        for name, attrs in graph()[1].items():
            script = attribute(attrs, "script")
            if script is not None:
                self.assertNotIn("{{ inputs.", script, name)

    def test_no_gate_no_children_references_inside(self):
        text, steps, edges = graph()
        self.assertRegex(text, r'(?m)^\s*on_failure="exit"\s*$')
        self.assertNotIn("hexagon", text)
        self.assertNotRegex(text, r"child_workflow\s*=")
        for reference in re.findall(r'"@([^"]+)"', text):
            self.assertTrue((SPEC / reference).is_file(), reference)
            self.assertNotIn("/", reference)


class NothingPushedTestCase(SimpleTestCase):
    """the spec workflow pushes nothing"""

    def test_nothing_pushed(self):
        run = settings()["run"]
        self.assertIs(run["pull_request"]["enabled"], False)
        self.assertIs(run["run_branch"]["push"], False)
        # GitHub permissions would replace the sandbox's read-only git access
        self.assertNotIn("integrations", run)
        self.assertEqual(
            run["artifacts"]["include"],
            [
                ".intentable/result.json",
                ".intentable/review.md",
            ],
        )


class ReviewerPromptsTestCase(SimpleTestCase):
    """reviewers are fresh, one lens each; the fidelity reviewer reads the decision record; reports only"""

    def test_three_lenses(self):
        named = {}
        for reviewer, lens in REVIEWERS.items():
            text = prompt(reviewer)
            self.assertIn(f"## Your lens: {lens}", text, reviewer)
            for other, other_lens in REVIEWERS.items():
                if other != reviewer:
                    self.assertNotIn(f"## Your lens: {other_lens}", text, reviewer)
            named[reviewer] = lens
        self.assertEqual(len(set(named.values())), 3)
        self.assertIn("readers the task list misses", prompt("risk"))
        self.assertIn("`openspec/config.yaml`", prompt("spec_fit"))
        self.assertIn("`AGENTS.md`", prompt("spec_fit"))
        self.assertIn("An unflagged one is blocking", prompt("fidelity"))

    def test_decision_record_and_bridge_comments(self):
        fidelity = prompt("fidelity")
        for needed in (
            "thread",
            "`AGENTS.md`",
            "`openspec/changes/archive/`",
            "{{ inputs.issue_thread }}",
        ):
            self.assertIn(needed, fidelity)
        for name in ("fidelity", "propose"):
            self.assertIn("<!-- intentable-bridge -->", prompt(name), name)
            self.assertIn("not the owner speaking", prompt(name), name)

    def test_fidelity_checks_each_point_of_the_feedback(self):
        text = prompt("fidelity")
        self.assertIn('`"revision": true`', text)
        self.assertIn("Check each point of it in the change's files, and each question it asks in the draft's `message`", text)
        self.assertIn("is blocking unless the message gives the reason", text)

    def test_reviewer_prompts(self):
        for reviewer in REVIEWERS:
            text = prompt(reviewer)
            self.assertIn(f"`.intentable/reviews/{reviewer}.md`", text, reviewer)
            for heading in (
                "SATISFIED: yes|no",
                "BLOCKING:",
                "NON-BLOCKING:",
                "CONFIRMED OK:",
            ):
                self.assertIn(heading, text, (reviewer, heading))
            self.assertIn("`none` under an empty heading", text, reviewer)
            self.assertIn("Edit nothing else", text, reviewer)
            self.assertIn("`.intentable/reviews/revise.md`", text, reviewer)

    def test_revise_prompt(self):
        text = prompt("revise")
        self.assertIn("Apply every blocking finding", text)
        self.assertIn("`.intentable/reviews/<round>/`", text)
        self.assertIn("`.intentable/reviews/round`", text)
        self.assertIn("two to four plain sentences", text)
        self.assertIn("SVG or HTML comments", text)
        self.assertIn("`#` fragments only", text)
        self.assertIn("`.intentable/reviews/revise.md`", text)
        self.assertIn("do not rename the change", text)
        self.assertIn("Do not change its `labels`", text)


class ProposePromptTestCase(SimpleTestCase):
    """the proposal prompt states the rules"""

    def test_the_prompt_gives_the_rules(self):
        text = prompt("propose")
        for needed in (
            "planning artifacts only",
            "`openspec/config.yaml`",
            "`AGENTS.md`",
            "Keep host and network names out",
            "open question",
            "two to four plain sentences",
            "no @-mentions",
            "`.intentable/draft.json`",
            "`needs-info`",
            "exactly one question",
        ):
            self.assertIn(needed, text, needed)

    def revision_section(self):
        return prompt("propose").split("## Feedback on a draft", 1)[1].split("## What to do", 1)[0]

    def test_the_propose_prompt_has_the_revision_section(self):
        text = self.revision_section()
        for needed in (
            "{{ inputs.feedback }}",
            "{{ inputs.change_name }}",
            "Don't write a new change",
            '`"revision": true`',
        ):
            self.assertIn(needed, text, needed)

    def test_the_prompt_asks_for_answers(self):
        text = self.revision_section()
        self.assertIn("answer each question the feedback asks", text)
        self.assertIn("name any request outside the issue's scope as one to file as its own issue", text)

    def test_the_prompt_limits_a_revision_after_g2(self):
        text = self.revision_section()
        self.assertIn("{{ inputs.revision_scope }}", text)
        self.assertIn("If what you may change is `sketches`", text)
        self.assertIn("change only files under `sketches/` and the design's \"Sketches\" section", text)
        self.assertIn("name in your message each request that would need the proposal itself changed", text)

    def test_the_prompt_gives_a_revisions_exceptions(self):
        text = self.revision_section()
        self.assertIn("Keep the change's name", text)
        # issue #26's first revision chained its draft after a validate that failed on warnings
        self.assertIn("With `--strict` a warning fails it too", text)
        self.assertIn("as a step of its own and not chained after another command", text)
        self.assertIn("run `cat .intentable/draft.json` from the repository's root", text)
        self.assertIn("Stop only once `.intentable/draft.json` is written", text)
        self.assertIn("don't send the issue back", text)
        self.assertIn("six plain sentences", text)

    def test_prompts_keep_one_sketch(self):
        text = self.revision_section()
        self.assertIn("delete the other sketches and their entries in `sketches/options.json`", text)
        self.assertIn("Don't add new variations", text)
        self.assertIn("`.intentable/main/sketch.md`", text)
        self.assertIn("keep it at one: don't add sketches back", prompt("revise"))

    def test_the_propose_agent_finishes_its_own_work(self):
        text = prompt("propose")
        for needed in (
            "Don't review the draft yourself",
            "Start no subagents and no background tasks",
            "stop only once `.intentable/draft.json` is written",
        ):
            self.assertIn(needed, text, needed)
        # every agent sees the goal; issue #14's propose agent ran its own reviewers from it
        goal = re.search(r'goal="([^"]*)"', (SPEC / "workflow.fabro").read_text()).group(1)
        self.assertNotIn("reviewed by", goal)

    def test_sketch_prompt_rules(self):
        text = prompt("sketch")
        for needed in (
            "system fonts only",
            "No scripts",
            "nothing loaded from another address",
            "`options.json`",
            "Do not generate images",
        ):
            self.assertIn(needed, text, needed)

    def test_sketch_prompt_names_the_checkers_elements(self):
        # issue #26's sketch used <kbd>, which the prompt didn't say was refused
        named = set(re.findall(r"`(\w+)`", re.search(r"Use only these elements: ([^.]*)\.", prompt("sketch")).group(1)))
        listed = re.search(r"SAFE_ELEMENTS = \{(.*?)\}", RESULT_CHECKER.read_text(), re.S).group(1)
        self.assertEqual(named, set(re.findall(r'"(\w+)"', listed)))


# the checkers, run as the workflow runs them, in a fresh folder with a fake openspec

RESULT_CHECKER = ROOT / "bin" / "check-intentable-result"
REVIEW_CHECKER = ROOT / "bin" / "check-intentable-reviews"
SAFE_SKETCH = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>A</title>
<style>body { font-family: system-ui, sans-serif; } .hero { background: url(data:image/png;base64,AAAA); }</style>
</head><body><header><h1>Venue hours</h1></header><main><table><tr><th>Day</th><td>9 to 5</td></tr></table>
<ul><li><a href="#top">Top</a></li></ul><img src="data:image/png;base64,AAAA" alt="map"></main></body></html>
"""
CHANGE_FILES = {
    ".openspec.yaml": "schema: spec-driven\n",
    "proposal.md": "## Why\n",
    "design.md": "## Context\n",
    "tasks.md": "- [ ] 1.1 Do it\n",
    "specs/venues/spec.md": "## ADDED Requirements\n",
}
SKETCH_FILES = {
    "sketches/a.html": SAFE_SKETCH,
    "sketches/b.html": SAFE_SKETCH,
    "sketches/c.html": SAFE_SKETCH,
    "sketches/options.json": json.dumps(
        [
            {"file": f"{s}.html", "label": f"Option {s}", "thesis": "Why it fits.", "risk": "What could go wrong."}
            for s in "abc"
        ]
    ),
}
DRAFT = {"change": "add-venue-hours", "labels": [], "message": "This covers opening hours. It leaves out holidays."}
FAKE_OPENSPEC = """#!/bin/sh
# stands in for openspec in tests: prints FAKE_OPENSPEC_OUTPUT, exits FAKE_OPENSPEC_STATUS
printf '%s\\n' "${FAKE_OPENSPEC_OUTPUT:-Change is valid}"
exit "${FAKE_OPENSPEC_STATUS:-0}"
"""


class Run:
    """a fresh folder laid out like the sandbox's checkout, with a fake openspec first on PATH"""

    def __init__(self, folder, draft=DRAFT, files=CHANGE_FILES, existing=("add-spek-pages-old",), route=None):
        self.folder = Path(folder)
        bin_dir = self.folder / "fake-bin"
        bin_dir.mkdir()
        fake = bin_dir / "openspec"
        fake.write_text(FAKE_OPENSPEC)
        fake.chmod(0o755)
        self.env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
        intentable = self.folder / ".intentable"
        intentable.mkdir()
        (intentable / "existing-changes.txt").write_text("".join(f"{name}\n" for name in existing))
        if draft is not None:
            (intentable / "draft.json").write_text(json.dumps(draft))
        if route is not None:
            (intentable / "route.json").write_text(json.dumps({"labels": route, "change": (draft or {}).get("change")}))
        change = (draft or {}).get("change")
        if change and files is not None:
            for relative, text in files.items():
                path = self.folder / "openspec" / "changes" / change / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)

    def path(self, relative):
        return self.folder / relative

    def run(self, script, *args, **env):
        done = subprocess.run(
            [sys.executable, str(script), *args],
            cwd=self.folder,
            capture_output=True,
            text=True,
            timeout=60,
            env={**self.env, **env},
        )
        return done.returncode, done.stdout + done.stderr

    def check(self, *args, **env):
        return self.run(RESULT_CHECKER, "spec", *args, **env)

    def reviews(self, *args):
        return self.run(REVIEW_CHECKER, *args)

    def write(self, relative, text):
        path = self.folder / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def git(self, *args):
        done = subprocess.run(["git", *args], cwd=self.folder, capture_output=True, text=True, timeout=60)
        assert done.returncode == 0, done.stderr
        return done.stdout.strip()

    def commit_all(self, message):
        """a commit of everything but .intentable/, as the sandbox's checkout and Fabro's checkpoints are"""
        self.write(".gitignore", ".intentable/\nfake-bin/\n")
        if not self.path(".git").exists():
            self.git("init", "--quiet")
            self.git("config", "user.email", "test@example.com")
            self.git("config", "user.name", "test")
        self.git("add", "-A")
        self.git("commit", "--quiet", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def passed_review(self):
        self.write(".intentable/reviews/outcome", "passed\n")
        self.write(".intentable/reviews/summary.md", "Passed by the reviewers after 1 round(s).\n")


def report(satisfied):
    return f"SATISFIED: {'yes' if satisfied else 'no'}\nBLOCKING:\n{'none' if satisfied else '- fix the thing'}\nNON-BLOCKING:\nnone\nCONFIRMED OK:\nnone\n"


class DraftFileTestCase(SimpleTestCase):
    """the draft is named in its own file; an issue that isn't ready goes back with a question"""

    def test_draft_check_reads_the_draft_file(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            status, output = run.check("--draft")
            self.assertEqual(status, 0, output)
            self.assertFalse(run.path(".intentable/result.json").exists())

    def test_not_ready(self):
        draft = {"state": "needs-info", "labels": ["clarity:3"], "message": "Should hours come from the venue's site?"}
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder, draft=draft, route=["clarity:3"])
            self.assertEqual(
                json.loads(run.reviews("--route")[1].strip().splitlines()[-1]), {"context_updates": {"route": "back"}}
            )
            status, output = run.check()
            self.assertEqual(status, 0, output)
            result = json.loads(run.path(".intentable/result.json").read_text())
            self.assertEqual(result, {"labels": ["clarity:3"], "state": "needs-info", "message": draft["message"]})

    def test_a_send_back_with_a_stray_change(self):
        draft = {"state": "needs-info", "labels": ["clarity:3"], "message": "Which venues?"}
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder, draft=draft)
            run.write("openspec/changes/stray/proposal.md", "x\n")
            status, output = run.check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("stray is new", output)

    def test_a_send_back_that_breaks_the_rules(self):
        base = {"state": "needs-info", "labels": ["clarity:3"], "message": "Which venues?"}
        for bad, needle in (
            ({"labels": ["clarity:4"]}, "clarity:1 to clarity:3"),
            ({"message": "Which venues? And when?"}, "one question"),
            ({"change": "add-venue-hours"}, "names no change"),
        ):
            with tempfile.TemporaryDirectory() as folder:
                run = Run(folder, draft={**base, **bad})
                status, output = run.check("--draft")
                self.assertEqual(status, 1, bad)
                self.assertIn(needle, output, bad)


class SpecResultTestCase(SimpleTestCase):
    """the spec result names the change; the summary is collected with the result"""

    def test_a_good_result(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            run.passed_review()
            status, output = run.check()
            self.assertEqual(status, 0, output)
            result = json.loads(run.path(".intentable/result.json").read_text())
            self.assertEqual(result["change"], "add-venue-hours")
            self.assertIsNone(result["state"])
            self.assertEqual(result["labels"], [])
            self.assertEqual(result["message"], DRAFT["message"])
            self.assertEqual(result["reviewed"], "passed")
            self.assertEqual(sorted(result["files"]), sorted(CHANGE_FILES))

    def test_summary_beside_the_result(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            run.passed_review()
            self.assertEqual(run.check()[0], 0)
            self.assertEqual(
                run.path(".intentable/review.md").read_text(), run.path(".intentable/reviews/summary.md").read_text()
            )
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            run.passed_review()
            self.assertEqual(run.check("--draft")[0], 0)
            self.assertFalse(run.path(".intentable/review.md").exists())


class ChangeNameTestCase(SimpleTestCase):
    """the change name is plain and new"""

    def test_a_name_that_isnt_plain(self):
        for name in ("../add-x", "Add Venue Hours", "add--x", "x" * 61):
            with tempfile.TemporaryDirectory() as folder:
                run = Run(folder, draft={**DRAFT, "change": name}, files=None)
                status, output = run.check()
                self.assertEqual(status, 1, name)
                self.assertIn("isn't a change name", output, name)

    def test_a_change_that_already_existed(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder, draft={**DRAFT, "change": "add-spek-pages"}, existing=["2026-11-02-add-spek-pages"])
            status, output = run.check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("already exists", output)

    def test_no_change_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder, files=None)
            status, output = run.check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("folder is missing", output)


class BoundsTestCase(SimpleTestCase):
    """spec drafts must be valid and collectable; they give no state and follow the message rules"""

    def test_a_state_or_another_label(self):
        for bad, needle in (({"state": "building"}, "building"), ({"labels": ["ai-shippable"]}, "ai-shippable")):
            with tempfile.TemporaryDirectory() as folder:
                run = Run(folder, draft={**DRAFT, **bad})
                status, output = run.check("--draft")
                self.assertEqual(status, 1, bad)
                self.assertIn(needle, output, bad)

    def test_too_many_files(self):
        files = {**CHANGE_FILES, **{f"specs/s{n}/spec.md": "x\n" for n in range(86)}}
        with tempfile.TemporaryDirectory() as folder:
            status, output = Run(folder, files=files).check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("91 files, at most 90", output)

    def test_a_file_fabro_wouldnt_collect(self):
        with tempfile.TemporaryDirectory() as folder:
            status, output = Run(folder, files={**CHANGE_FILES, "specs/dist/spec.md": "x\n"}).check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("specs/dist/spec.md", output)
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            run.path("openspec/changes/add-venue-hours/sketch.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe")
            status, output = run.check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("sketch.png", output)

    def test_each_folder_fabro_skips(self):
        for segment in ("dist", "venv", ".pnpm-store", ".npm", ".next", "__pycache__", ".tox", ".pytest_cache"):
            with tempfile.TemporaryDirectory() as folder:
                path = f"specs/{segment}/spec.md"
                status, output = Run(folder, files={**CHANGE_FILES, path: "x\n"}).check("--draft")
                self.assertEqual(status, 1, segment)
                self.assertIn(path, output)

    def test_a_file_too_large(self):
        for big in ("x" * (256 * 1024 + 1), "x\n" * 20001):
            with tempfile.TemporaryDirectory() as folder:
                status, output = Run(folder, files={**CHANGE_FILES, "design.md": big}).check("--draft")
                self.assertEqual(status, 1)
                self.assertIn("design.md is too large", output)

    def test_invalid_change(self):
        with tempfile.TemporaryDirectory() as folder:
            status, output = Run(folder).check(
                "--draft", FAKE_OPENSPEC_STATUS="1", FAKE_OPENSPEC_OUTPUT="Change 'add-venue-hours' has issues"
            )
            self.assertEqual(status, 1)
            self.assertIn("Change 'add-venue-hours' has issues", output)

    def test_a_message_that_mentions_someone(self):
        with tempfile.TemporaryDirectory() as folder:
            status, output = Run(folder, draft={**DRAFT, "message": "Thanks @sooz, this covers hours."}).check(
                "--draft"
            )
            self.assertEqual(status, 1)
            self.assertIn("mention no one", output)


class SketchTestCase(SimpleTestCase):
    """sketches: required with needs-design, checked as soon as they are made, safe to publish; labels fixed"""

    def sketch_run(self, folder, extra=None, design="sketches/a.html sketches/b.html sketches/c.html", **kwargs):
        files = {**CHANGE_FILES, **SKETCH_FILES, "design.md": design, **(extra or {})}
        return Run(folder, draft={**DRAFT, "labels": ["needs-design"]}, files=files, **kwargs)

    def test_sketches_required_with_needs_design(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.sketch_run(folder).check("--sketches")[0], 0)
        with tempfile.TemporaryDirectory() as folder:
            run = self.sketch_run(folder)
            run.path("openspec/changes/add-venue-hours/sketches/c.html").unlink()
            status, output = run.check("--sketches")
            self.assertEqual(status, 1)
            self.assertIn("sketches/c.html is missing", output)
        with tempfile.TemporaryDirectory() as folder:
            status, output = self.sketch_run(folder, design="sketches/b.html sketches/c.html").check("--sketches")
            self.assertEqual(status, 1)
            self.assertIn("doesn't link sketches/a.html", output)

    def test_unsafe_sketch_caught_before_review(self):
        unsafe = SAFE_SKETCH.replace(
            "<title>A</title>", '<title>A</title><link rel="stylesheet" href="https://x.example/a.css">'
        )
        with tempfile.TemporaryDirectory() as folder:
            status, output = self.sketch_run(folder, extra={"sketches/b.html": unsafe}).check("--sketches")
            self.assertEqual(status, 1)
            self.assertIn("sketches/b.html", output)

    def test_first_draft_check_without_sketches(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder, draft={**DRAFT, "labels": ["needs-design"]})
            status, output = run.check("--draft")
            self.assertEqual(status, 0, output)

    def test_a_sketch_with_a_script(self):
        for bad in ("<script>alert(1)</script>", '<div onclick="go()">x</div>', '<a href="jav&#x61;script:go()">x</a>'):
            with tempfile.TemporaryDirectory() as folder:
                sketch = SAFE_SKETCH.replace("</main>", bad + "</main>")
                status, output = self.sketch_run(folder, extra={"sketches/b.html": sketch}).check("--draft")
                self.assertEqual(status, 1, bad)
                self.assertIn("sketches/b.html", output, bad)

    def test_a_sketch_that_calls_out(self):
        for bad in (
            '<style>@import url("https://fonts.googleapis.com/css2?family=Open+Sans");</style>',
            '<div style="background: url(//cdn.example/x.png)">x</div>',
            '<form action="https://example.org"><button>Go</button></form>',
            '<iframe srcdoc="&lt;script&gt;go()&lt;/script&gt;"></iframe>',
            '<img src="https://example.org/x.png" alt="x">',
        ):
            with tempfile.TemporaryDirectory() as folder:
                sketch = SAFE_SKETCH.replace("</main>", bad + "</main>")
                status, output = self.sketch_run(folder, extra={"sketches/b.html": sketch}).check("--draft")
                self.assertEqual(status, 1, bad)
                self.assertIn("sketches/b.html", output, bad)

    def test_the_behavior_property(self):
        with tempfile.TemporaryDirectory() as folder:
            sketch = SAFE_SKETCH.replace("</main>", '<p style="scroll-behavior:smooth">x</p></main>')
            status, output = self.sketch_run(folder, extra={"sketches/b.html": sketch}).check("--draft")
            self.assertEqual(status, 0, output)
        with tempfile.TemporaryDirectory() as folder:
            sketch = SAFE_SKETCH.replace("</main>", '<p style="behavior:url(#x)">x</p></main>')
            status, output = self.sketch_run(folder, extra={"sketches/b.html": sketch}).check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("behavior", output)

    def test_a_sketch_with_text_elements(self):
        # issue #26's sketch was refused for <kbd>
        text = "<p>Press <kbd>/</kbd>, <q>quoted</q> <cite>a</cite> <var>n</var> <samp>out</samp> <dfn>term</dfn> <del>old</del> <ins>new</ins>long<wbr>word</p><address>Boston</address>"
        with tempfile.TemporaryDirectory() as folder:
            sketch = SAFE_SKETCH.replace("</main>", text + "</main>")
            status, output = self.sketch_run(folder, extra={"sketches/b.html": sketch}).check("--sketches")
            self.assertEqual(status, 0, output)

    def test_a_sketch_browsers_read_differently(self):
        refresh = '<meta http-equiv=refresh content="0;url=https://evil.example/">'
        for bad in (
            f"<!-->{refresh}-->",
            "<!---><script>go()</script>-->",
            "<!-- a note -->",
            "<!x><p>x</p>",
            f"<svg><style>{refresh}</style></svg>",
            f"<svg><title>{refresh}</title></svg>",
            "<style/>@import url(https://evil.example/x.css)</style>",
            "<style><img src=x></style>",
            '<meta charset="iso-2022-jp">',
            "<div style=\"background:image-set('https://evil.example/x.png' 1x)\">x</div>",
            '<p title="url(https://evil.example/x)">x</p>',
        ):
            with tempfile.TemporaryDirectory() as folder:
                sketch = SAFE_SKETCH.replace("</main>", bad + "</main>")
                status, output = self.sketch_run(folder, extra={"sketches/b.html": sketch}).check("--draft")
                self.assertEqual(status, 1, bad)
                self.assertIn("sketches/b.html", output, bad)

    def test_options_for_each_sketch(self):
        good = json.loads(SKETCH_FILES["sketches/options.json"])
        for bad, needle in (
            ("not json", "isn't JSON"),
            (json.dumps({"options": good}), "must be a list"),
            (json.dumps(good[:2]), "no entry for c.html"),
            (json.dumps([{**good[0], "risk": " "}, good[1], good[2]]), "no risk for a.html"),
            (json.dumps([{**good[0], "thesis": None}, good[1], good[2]]), "no thesis for a.html"),
        ):
            with tempfile.TemporaryDirectory() as folder:
                status, output = self.sketch_run(folder, extra={"sketches/options.json": bad}).check("--sketches")
                self.assertEqual(status, 1, bad)
                self.assertIn(needle, output, bad)

    def test_a_safe_sketch(self):
        with tempfile.TemporaryDirectory() as folder:
            status, output = self.sketch_run(folder).check("--draft")
            self.assertEqual(status, 0, output)

    def test_a_sketch_lost_in_revise(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.sketch_run(folder, route=["needs-design"])
            run.passed_review()
            run.path("openspec/changes/add-venue-hours/sketches/c.html").unlink()
            status, output = run.check()
            self.assertEqual(status, 1)
            self.assertIn("sketches/c.html is missing", output)

    def test_revise_adds_needs_design(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder, draft={**DRAFT, "labels": ["needs-design"]}, route=[])
            status, output = run.check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("labels changed after routing", output)

    def test_revise_renames_the_change(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            self.assertEqual(run.reviews("--route")[0], 0)
            draft = {**DRAFT, "change": "add-venue-times"}
            run.write(".intentable/draft.json", json.dumps(draft))
            run.write("openspec/changes/add-venue-times/proposal.md", "x\n")
            status, output = run.check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("renamed after routing", output)

    def test_route_records_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder, draft={**DRAFT, "labels": ["needs-design"]})
            status, output = run.reviews("--route")
            self.assertEqual(status, 0, output)
            self.assertEqual(json.loads(output.strip().splitlines()[-1]), {"context_updates": {"route": "sketch"}})
            self.assertEqual(
                json.loads(run.path(".intentable/route.json").read_text()),
                {"labels": ["needs-design"], "change": DRAFT["change"]},
            )
        with tempfile.TemporaryDirectory() as folder:
            output = Run(folder).reviews("--route")[1]
            self.assertEqual(json.loads(output.strip().splitlines()[-1]), {"context_updates": {"route": "review"}})


class ReviewLoopTestCase(SimpleTestCase):
    """the review loop ends; the review is summed up for Nate"""

    def round(self, run, risk=True, spec_fit=True, fidelity=True):
        for lens, ok in (("risk", risk), ("spec_fit", spec_fit), ("fidelity", fidelity)):
            if ok is not None:
                run.write(f".intentable/reviews/{lens}.md", report(ok))
        status, output = run.reviews()
        self.assertEqual(status, 0, output)
        return json.loads(output.strip().splitlines()[-1])["context_updates"]["review_done"]

    def test_all_satisfied(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            self.assertEqual(self.round(run), "true")
            self.assertEqual(run.path(".intentable/reviews/outcome").read_text().strip(), "passed")
            self.assertTrue(
                run.path(".intentable/reviews/summary.md")
                .read_text()
                .startswith("Passed by the reviewers after 1 round(s).")
            )

    def test_one_not_satisfied(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            self.assertEqual(self.round(run, risk=False), "false")
            self.assertFalse(run.path(".intentable/reviews/outcome").exists())

    def test_the_round_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            for _ in range(4):
                self.assertEqual(self.round(run, risk=False), "false")
            self.assertEqual(self.round(run, risk=False), "true")
            self.assertEqual(run.path(".intentable/reviews/outcome").read_text().strip(), "not-passed")

    def test_missing_report(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.round(Run(folder), fidelity=None), "false")

    def test_summary_written(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            self.round(run, risk=False)
            run.write(".intentable/reviews/revise.md", "- fix the thing: fixed in design.md\n")
            self.round(run)
            text = run.path(".intentable/reviews/summary.md").read_text()
            self.assertTrue(text.startswith("Passed by the reviewers after 2 round(s).\n"))
            self.assertIn("- fix the thing", text)
            self.assertIn("fixed in design.md", text)
            # the notes are filed with the round they answer
            self.assertTrue(run.path(".intentable/reviews/1/revise.md").is_file())
            self.assertEqual(run.path(".intentable/reviews/outcome").read_text().strip(), "passed")

    def test_last_rounds_other_findings_in_the_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            run.write(
                ".intentable/reviews/risk.md",
                "SATISFIED: yes\nBLOCKING:\nnone\nNON-BLOCKING:\n- a small risk\nCONFIRMED OK:\n- fine\n",
            )
            self.round(run, risk=None)
            text = run.path(".intentable/reviews/summary.md").read_text()
            self.assertIn("- a small risk", text)
            self.assertNotIn("- fine", text)

    def test_a_fenced_report(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            run.write(".intentable/reviews/risk.md", "```\n" + report(True) + "```\n")
            self.assertEqual(self.round(run, risk=None), "true")

    def test_summary_of_a_review_not_passed(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder)
            for _ in range(5):
                self.round(run, spec_fit=False)
            self.assertTrue(
                run.path(".intentable/reviews/summary.md")
                .read_text()
                .startswith("Not passed by the reviewers after 5 rounds.")
            )
            self.assertEqual(run.path(".intentable/reviews/outcome").read_text().strip(), "not-passed")

    def test_record_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Run(folder, files=CHANGE_FILES)
            (run.path("openspec/changes/archive/2026-11-02-add-spek-pages")).mkdir(parents=True)
            head = run.commit_all("checkout")
            self.assertEqual(run.reviews("--record-existing")[0], 0)
            self.assertEqual(
                run.path(".intentable/existing-changes.txt").read_text(), "2026-11-02-add-spek-pages\nadd-venue-hours\n"
            )
            # the base a sketches-only revision is compared with
            self.assertEqual(run.path(".intentable/base").read_text().strip(), head)


REVISION = {**DRAFT, "labels": ["needs-design"], "revision": True}
DESIGN_WITH_SKETCHES = "## Context\n\nThe venue page.\n\n## Sketches\n\n- sketches/a.html\n- sketches/b.html\n- sketches/c.html\n\n## Risks\n\nNone.\n"
ONE_SKETCH = {
    "sketches/c.html": SAFE_SKETCH,
    "sketches/options.json": json.dumps([{"file": "c.html", "label": "Option c", "thesis": "Why.", "risk": "Risk."}]),
}


class RevisionTestCase(SimpleTestCase):
    """a revision answers the feedback: checked like a new draft, on its own change, narrowed to one sketch"""

    def revision_run(self, folder, draft=REVISION, sketches=SKETCH_FILES, design=DESIGN_WITH_SKETCHES, **kwargs):
        files = {**CHANGE_FILES, **sketches, "design.md": design}
        return Run(folder, draft=draft, files=files, existing=("add-venue-hours",), **kwargs)

    def test_a_revision_of_an_existing_change(self):
        with tempfile.TemporaryDirectory() as folder:
            status, output = self.revision_run(folder).check("--draft")
            self.assertEqual(status, 0, output)

    def test_a_revision_that_makes_a_new_change(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.revision_run(folder)
            run.write("openspec/changes/add-swipe-deck/proposal.md", "x\n")
            status, output = run.check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("add-swipe-deck is new", output)
        with tempfile.TemporaryDirectory() as folder:
            # a revision of a change that wasn't there before the run
            run = Run(folder, draft=REVISION, files={**CHANGE_FILES, **SKETCH_FILES, "design.md": DESIGN_WITH_SKETCHES})
            status, output = run.check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("didn't exist before the run", output)

    def test_a_revision_that_asks_a_question_back(self):
        draft = {**REVISION, "state": "needs-info", "labels": ["clarity:3"], "message": "Which video?"}
        with tempfile.TemporaryDirectory() as folder:
            status, output = self.revision_run(folder, draft=draft).check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("a revision can't send the issue back", output)

    def test_an_unsafe_sketch_in_a_revision(self):
        unsafe = SAFE_SKETCH.replace("</body>", "<script>alert(1)</script></body>")
        with tempfile.TemporaryDirectory() as folder:
            status, output = self.revision_run(folder, sketches={**ONE_SKETCH, "sketches/c.html": unsafe}).check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("sketches/c.html", output)

    def test_one_sketch_after_a_pick(self):
        design = DESIGN_WITH_SKETCHES.replace("- sketches/a.html\n- sketches/b.html\n", "")
        with tempfile.TemporaryDirectory() as folder:
            run = self.revision_run(folder, sketches=ONE_SKETCH, design=design, route=["needs-design"])
            run.passed_review()
            status, output = run.check()
            self.assertEqual(status, 0, output)

    def test_two_sketches(self):
        two = {k: v for k, v in SKETCH_FILES.items() if k != "sketches/b.html"}
        with tempfile.TemporaryDirectory() as folder:
            run = self.revision_run(folder, sketches=two, route=["needs-design"])
            run.passed_review()
            status, output = run.check()
            self.assertEqual(status, 1)
            self.assertIn("a new draft has three options and a narrowed revision one", output)
        with tempfile.TemporaryDirectory() as folder:
            # one sketch is for a narrowed revision only
            run = Run(folder, draft={**DRAFT, "labels": ["needs-design"]}, route=["needs-design"],
                      files={**CHANGE_FILES, **ONE_SKETCH, "design.md": "sketches/c.html"})
            run.passed_review()
            status, output = run.check()
            self.assertEqual(status, 1)
            self.assertIn("a new draft has three options and a narrowed revision one", output)

    def test_two_sketches_at_the_first_check(self):
        two = {k: v for k, v in SKETCH_FILES.items() if k != "sketches/b.html"}
        with tempfile.TemporaryDirectory() as folder:
            status, output = self.revision_run(folder, sketches=two).check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("sketches/b.html is missing", output)

    def test_a_revisions_result(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.revision_run(folder, route=["needs-design"])
            run.passed_review()
            status, output = run.check()
            self.assertEqual(status, 0, output)
            result = json.loads(run.path(".intentable/result.json").read_text())
            self.assertIs(result["revision"], True)
            self.assertEqual(result["change"], "add-venue-hours")
            self.assertEqual(result["reviewed"], "passed")
            self.assertIn("sketches/c.html", result["files"])

    def test_a_revision_goes_straight_to_review(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.revision_run(folder)
            status, output = run.reviews("--route")
            self.assertEqual(status, 0, output)
            self.assertEqual(json.loads(output.strip().splitlines()[-1]), {"context_updates": {"route": "revised"}})
            self.assertEqual(
                json.loads(run.path(".intentable/route.json").read_text()),
                {"labels": ["needs-design"], "change": "add-venue-hours"},
            )

    def scoped_run(self, folder):
        """a sketches-only revision: base recorded at checkout, then the agent's edits in a checkpoint commit"""
        run = self.revision_run(folder, draft={**REVISION, "scope": "sketches"})
        run.commit_all("draft branch")
        self.assertEqual(run.reviews("--record-existing")[0], 0)
        return run

    def test_a_sketch_only_revision_that_changes_the_spec(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.scoped_run(folder)
            run.write("openspec/changes/add-venue-hours/specs/venues/spec.md", "## ADDED Requirements\n\nMore.\n")
            run.commit_all("checkpoint after propose")
            status, output = run.check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("changed specs/venues/spec.md", output)
        with tempfile.TemporaryDirectory() as folder:
            run = self.scoped_run(folder)
            design = DESIGN_WITH_SKETCHES.replace("The venue page.", "The venue page, with video.")
            run.write("openspec/changes/add-venue-hours/design.md", design)
            status, output = run.check("--draft")
            self.assertEqual(status, 1)
            self.assertIn("outside its \"Sketches\" section", output)

    def test_a_sketch_only_revision_that_changes_a_sketch(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.scoped_run(folder)
            run.write("openspec/changes/add-venue-hours/sketches/c.html", SAFE_SKETCH.replace("Venue hours", "Venue video"))
            run.write(
                "openspec/changes/add-venue-hours/design.md",
                DESIGN_WITH_SKETCHES.replace("- sketches/c.html\n", "- sketches/c.html, now with video\n"),
            )
            run.commit_all("checkpoint after propose")
            status, output = run.check("--draft")
            self.assertEqual(status, 0, output)

    def test_a_revision_on_a_branch_cut_before_this_change(self):
        # the draft branch's own bin/ predates the revision rules; the run checks with main's copy
        old = subprocess.run(
            ["git", "show", "5aff796:bin/check-intentable-result"], cwd=ROOT, capture_output=True, text=True
        )
        if old.returncode != 0:
            self.skipTest("the fork's history isn't in this checkout")
        with tempfile.TemporaryDirectory() as folder:
            run = self.revision_run(folder)
            run.write("bin/check-intentable-result", old.stdout)
            status, output = run.run(run.path("bin/check-intentable-result"), "spec", "--draft")
            self.assertEqual(status, 1)
            self.assertIn("already exists", output)
            run.write(f"{MAIN}/check-intentable-result", RESULT_CHECKER.read_text())
            status, output = run.run(run.path(f"{MAIN}/check-intentable-result"), "spec", "--draft")
            self.assertEqual(status, 0, output)


class GuideTestCase(SimpleTestCase):
    """a guide explains the spec workflow"""

    def test_guide(self):
        guide = (ROOT / "docs" / "FABRO.md").read_text()
        section = guide.split("#### spec", 1)[1]
        for needed in (
            "Fabro's record of the files the run changed",
            "risk, spec fit, fidelity",
            "five-round limit",
            "the bridge commits the draft",
            "##### revisions",
            "`revision_scope`",
            "one sketch is allowed only in a revision",
            "`.intentable/main/`",
        ):
            self.assertIn(needed, section, needed)
