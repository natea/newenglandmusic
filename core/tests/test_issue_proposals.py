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
            "python3 bin/check-intentable-result spec --draft",
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
            "python3 bin/check-intentable-result spec --draft",
        )
        self.assertEqual(next_steps(edges, "recheck"), {("fork", None)})
        self.assertEqual(
            attribute(steps["finish"], "script"),
            "python3 bin/check-intentable-result spec",
        )
        self.assertEqual(next_steps(edges, "finish"), {("exit", None)})
        self.assertEqual(settings()["workflow"]["graph"], "workflow.fabro")

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
            "python3 bin/check-intentable-result spec --sketches",
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
        self.assertEqual(sorted(settings()["run"]["inputs"]), sorted(INPUTS))
        for key in INPUTS:
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
            self.assertEqual(run.reviews("--record-existing")[0], 0)
            self.assertEqual(
                run.path(".intentable/existing-changes.txt").read_text(), "2026-11-02-add-spek-pages\nadd-venue-hours\n"
            )


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
        ):
            self.assertIn(needed, section, needed)
