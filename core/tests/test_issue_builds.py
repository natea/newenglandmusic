"""the build workflow the intentable bridge starts after Nate's /approve (issue-builds)

run with: venv/bin/python manage.py test core.tests.test_issue_builds
"""

import re
import subprocess
import tomllib
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / ".fabro" / "workflows" / "build"
INPUTS = ["issue_number", "issue_title", "issue_body", "issue_author", "issue_thread", "change_name"]


def settings(name="build"):
    with open(ROOT / ".fabro" / "workflows" / name / "workflow.toml", "rb") as f:
        return tomllib.load(f)


def graph_text():
    return (BUILD / "workflow.fabro").read_text()


def parse_nodes(text):
    """every node's attributes, reading each quoted value to its closing quote

    the parser in test_fabro_config.py stops at the first line ending in ], which
    a multi-line script can contain; this one walks the text a character at a time
    """
    nodes = {}
    # find node starts only outside quoted values, where a script's own [ can't be mistaken for one
    blanked, quoted = [], False
    i = 0
    while i < len(text):
        ch = text[i]
        if quoted and ch == "\\" and i + 1 < len(text):
            blanked.append("  ")
            i += 2
            continue
        if ch == '"':
            quoted = not quoted
            blanked.append(ch)
        else:
            blanked.append(" " if quoted and ch != "\n" else ch)
        i += 1
    for match in re.finditer(r"^[ \t]*(\w+)[ \t]*\[", "".join(blanked), re.MULTILINE):
        name, i = match.group(1), match.end()
        attrs, key, buf, in_quote = {}, None, "", False
        while i < len(text):
            ch = text[i]
            if in_quote:
                if ch == "\\" and i + 1 < len(text):
                    buf += text[i + 1]
                    i += 2
                    continue
                if ch == '"':
                    in_quote = False
                    attrs[key] = buf
                    key, buf = None, ""
                else:
                    buf += ch
            elif ch == '"':
                in_quote = True
            elif ch == "=":
                key, buf = buf.strip().strip(","), ""
            elif ch in ",]\n" and key is not None and buf.strip():
                attrs[key] = buf.strip()
                key, buf = None, ""
            elif ch not in ",\n":
                buf += ch
            if not in_quote and ch == "]":
                break
            i += 1
        nodes[name] = attrs
    return nodes


def steps():
    """the graph's steps, other than the graph's own attributes and start and exit"""
    return {n: a for n, a in parse_nodes(graph_text()).items() if n not in ("graph", "start", "exit")}


def commands():
    return {n: a for n, a in steps().items() if a.get("shape") == "parallelogram"}


class BuildFilesTestCase(SimpleTestCase):
    """issue-builds: The workflow's files are committed"""

    def test_nothing_ignored(self):
        files = [str(p.relative_to(ROOT)) for p in BUILD.rglob("*") if p.is_file()]
        self.assertTrue(files)
        result = subprocess.run(["git", "check-ignore", *files], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout, "", "git ignores files of the build workflow")


class BuildSettingsTestCase(SimpleTestCase):
    """issue-builds: inputs, and what the build pushes"""

    def test_declared_inputs(self):
        self.assertEqual(settings()["run"]["inputs"], {name: "" for name in INPUTS})

    def test_build_settings(self):
        run = settings()["run"]
        self.assertIs(run["run_branch"]["push"], True)
        self.assertIs(run["pull_request"]["enabled"], False)
        self.assertNotIn("github", run)
        self.assertEqual(run["artifacts"]["include"], [".intentable/result.json", ".intentable/pull-request.md"])

    def test_the_other_workflows_still_push_nothing(self):
        for name in ("triage", "clarify", "spec"):
            run = settings(name)["run"]
            self.assertIs(run["run_branch"]["push"], False, name)
            self.assertIs(run["pull_request"]["enabled"], False, name)


class BuildSetupTestCase(SimpleTestCase):
    """issue-builds: Setup installs what the tests need"""

    def test_setup_tools(self):
        setup = steps()["setup"]
        script = setup["script"]
        for tool in ("@anthropic-ai/claude-code", "@agentclientprotocol/claude-agent-acp", "@fission-ai/openspec"):
            self.assertRegex(script, re.escape(tool) + r"@\d+\.\d+\.\d+(\s|$)", f"{tool} isn't pinned")
        for needed in ("uv python install 3.11", "requirements-dev.txt", "postgresql", "140000", "chromium", "compilescss"):
            self.assertIn(needed, script)
        self.assertIn(".intentable/test.env", script)
        self.assertIn("nycnoise.settings.test", script)
        self.assertIn("git rev-parse HEAD > .intentable/start", script)
        self.assertRegex(setup.get("timeout", ""), r"^\d+m$")

    def test_setup_checks_the_tree(self):
        script = steps()["setup"]["script"].rstrip()
        last = script.splitlines()[-1]
        self.assertIn("git status --porcelain", last)
        self.assertIn("exit 1", last)


class BuildCommandsTestCase(SimpleTestCase):
    """issue-builds: No input reaches a command; The build is self-contained"""

    def test_commands_without_inputs(self):
        self.assertTrue(commands())
        for name, attrs in commands().items():
            self.assertNotIn("{{", attrs["script"], f"{name} contains an input")

    def test_no_script_from_the_checkout(self):
        # a command that runs something from the repository's bin/: as a command, or through an interpreter
        runs = re.compile(r"(^|[;&|(]\s*|\b(python3?|sh|bash|exec)\s+|\./)bin/|\[\s*'bin/|'bin/[\w.-]+'\s*\]")
        for name, attrs in commands().items():
            self.assertNotRegex(attrs["script"], runs, f"{name} runs a script from the repository's bin/")
        self.assertRegex("python3 bin/check-intentable-result", runs)
        self.assertNotRegex("venv/bin/python manage.py test", runs)

    def test_the_parser_reads_whole_scripts(self):
        nodes = parse_nodes('a [shape=parallelogram, script="\nX = [1]\nprint(X)\n"]\nb [label="B"]\n')
        self.assertEqual(nodes["a"]["script"], "\nX = [1]\nprint(X)\n")
        self.assertEqual(nodes["b"], {"label": "B"})


def prompt(name):
    return (BUILD / f"{name}.md").read_text()


AGENTS = ("apply", "refactor")
FORBIDDEN = (
    "merge commit",
    "push",
    "closing keyword",
    "`.github/`",
    "`.fabro/`",
    "`bin/publish-spek-page`",
    "`@`",
    "subagents or background tasks",
)


class BuildAgentsTestCase(SimpleTestCase):
    """issue-builds: the apply and refactor agents"""

    def test_the_prompts_name_the_change_not_the_thread(self):
        for name in AGENTS:
            text = prompt(name)
            self.assertIn("{{ inputs.change_name }}", text, name)
            used = set(re.findall(r"\{\{ inputs\.(\w+) \}\}", text))
            self.assertLessEqual(used, {"change_name", "issue_number", "issue_title"}, name)

    def test_acp_agents_only(self):
        agents = {name for name, attrs in steps().items() if attrs.get("type") == "agent"}
        self.assertEqual(agents, set(AGENTS))
        for name in AGENTS:
            self.assertEqual(steps()[name]["backend"], "acp", name)
            self.assertEqual(steps()[name]["acp.command"], "claude-agent-acp", name)
            self.assertEqual(steps()[name]["prompt"], f"@{name}.md", name)
        for name, attrs in steps().items():
            if name not in AGENTS:
                self.assertNotIn("prompt", attrs, f"{name} is a prompt stage")
        # every agent sees the goal; one worded like an instruction steers them
        goal = parse_nodes(graph_text())["graph"]["goal"]
        self.assertNotRegex(goal.lower(), r"\b(build|apply|refactor|commit) (the|a|each|every)\b")

    def test_the_apply_prompt_states_the_commit_rule(self):
        text = prompt("apply")
        for needed in (
            "one `## N.` group at a time",
            "Tick the box of each task you did",
            "commit the group's work and its ticks together, as one commit",
            "Never commit on a failing suite",
            "The subject says what the group did",
            ".intentable/test.env",
        ):
            self.assertIn(needed, text, needed)

    def test_the_apply_prompt_says_what_to_leave(self):
        text = prompt("apply")
        for needed in (
            "is left unticked",
            "a check by hand in a browser, or a live check against an outside system",
            "Nothing else counts",
            "`left_for_people`",
        ):
            self.assertIn(needed, text, needed)

    def test_the_apply_prompt_says_when_to_stop(self):
        text = prompt("apply")
        for needed in ("If a group can't be made to pass, stop", "Commit nothing for that group", "discard its changes", "`stopped`"):
            self.assertIn(needed, text, needed)

    def test_no_question_asked(self):
        self.assertNotIn("human", graph_text().lower())
        for name in AGENTS:
            self.assertIn("never ask and wait for an answer", prompt(name).lower(), name)
        self.assertIn("put the question in your message", prompt("apply"))
        self.assertIn("The answer will come through the change's own artifacts", prompt("apply"))
        self.assertIn('leave it out, and note it under "For Nate"', prompt("refactor"))

    def test_the_forbidden_list(self):
        for name in AGENTS:
            never = prompt(name).split("## Never", 1)[1].split("\n## ", 1)[0]
            for needed in FORBIDDEN:
                self.assertIn(needed, never, f"{name}: {needed}")

    def test_the_prompts_say_to_leave_a_clean_tree(self):
        for name in AGENTS:
            text = prompt(name)
            self.assertIn("clean working tree", text, name)
            self.assertIn("git restore --staged --worktree .", text, name)

    def test_the_refactor_prompt_states_the_rules(self):
        text = prompt("refactor")
        for needed in (
            "at most one commit",
            "only when the suite passes",
            "No change in behaviour",
            "no test that passed before fails",
            "Renames go through the whole project",
            "Break up a long function",
            "Extract logic expressed more than once",
            "Correct the comments",
            "Names say what the thing is",
            "never act on them",
            "a circular dependency or a layering violation",
            "code that looks dead",
            "a new module or grouping, or moving code across a module or layer boundary",
        ):
            self.assertIn(needed, text, needed)
        self.assertNotIn("_workflows/", text)


import json
import os
import shutil
import sys
import tempfile
from unittest import skipUnless

CHANGE = "export-venues-csv"
TASKS = "## 1. Export\n\n- [ ] 1.1 Add the export\n- [ ] 1.2 Test it\n\n## 2. Admin\n\n- [ ] 2.1 Add the button\n- [ ] 2.2 Check it by hand in a browser\n"


def script(name):
    return steps()[name]["script"]


class Repo:
    """a temporary git repository on a draft branch, with a G2 commit the run targets"""

    def __init__(self, tasks=TASKS):
        self.dir = Path(tempfile.mkdtemp(prefix="build-check-"))
        self.git("init", "-q", "-b", "change/" + CHANGE)
        self.git("config", "user.email", "fabro@example.com")
        self.git("config", "user.name", "Fabro")
        self.write(".gitignore", ".intentable/\n")
        self.write(f"openspec/changes/{CHANGE}/tasks.md", tasks)
        self.commit("Draft proposal " + CHANGE)
        self.git("commit", "-q", "--allow-empty", "-m", f"Confirm proposal {CHANGE} (G2)")
        self.write(".intentable/start", self.git("rev-parse", "HEAD").strip() + "\n")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.dir, capture_output=True, text=True, check=True).stdout

    def write(self, relative, text):
        path = self.dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, message, files=None):
        for relative, text in (files or {}).items():
            self.write(relative, text)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)

    def tick(self, *tasks):
        path = self.dir / "openspec" / "changes" / CHANGE / "tasks.md"
        text = path.read_text()
        for task in tasks:
            text = text.replace(f"- [ ] {task} ", f"- [x] {task} ")
        path.write_text(text)

    def record(self, **fields):
        record = {"change": CHANGE, "outcome": "complete", "message": "The venue list has an export button.", "left_for_people": []}
        record.update(fields)
        self.write(".intentable/build.json", json.dumps(record))

    def built(self, left=True):
        """two task-group commits, empty checkpoints and a refactoring commit, with every box ticked"""
        self.commit("fabro(RUN1): setup (succeeded)")
        self.tick("1.1", "1.2")
        self.commit("Add the venue export", {"core/export.py": "def export():\n    pass\n"})
        self.tick("2.1", *(() if left else ("2.2",)))
        self.commit("Add the export button to the admin", {"core/admin.py": "BUTTON = 1\n"})
        self.commit("fabro(RUN1): apply (succeeded)")
        self.commit("Refactor " + CHANGE, {"core/export.py": "def export():\n    return []\n"})
        self.commit("fabro(RUN1): refactor (succeeded)")

    def run(self, name, suite="true"):
        env = {**os.environ, "BUILD_TEST_COMMAND": suite}
        return subprocess.run([sys.executable, "-c", script(name)], cwd=self.dir, capture_output=True, text=True, env=env)

    def result(self):
        return json.loads((self.dir / ".intentable" / "result.json").read_text())

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class BuildGraphTestCase(SimpleTestCase):
    """issue-builds: A build workflow exists; the scripts are inline"""

    def test_the_build_graph(self):
        text = graph_text()
        self.assertEqual(set(steps()), {"setup", "apply", "route", "refactor", "finish"})
        self.assertIn('on_failure="exit"', text)
        self.assertRegex(text, r'route -> refactor \[condition="context\.route=refactor"\]')
        self.assertRegex(text, r"route -> finish\n")
        self.assertIn("refactor -> finish -> exit", text)
        self.assertEqual(steps()["route"]["output_schema"], "routing")
        self.assertRegex(steps()["finish"].get("timeout", ""), r"^\d+m$")

    def test_inline_scripts_without_escapes(self):
        for name in ("route", "finish"):
            self.assertEqual(steps()[name]["language"], "python", name)
            body = script(name)
            self.assertNotIn("\\", body, name)
            self.assertNotIn('"', body, name)
            self.assertNotIn("{{", body, name)
            compile(body, name, "exec")

    def test_setup_and_finish_check_the_tree(self):
        body = script("finish")
        self.assertGreater(body.index("'status', '--porcelain'"), body.index("result.json"))
        self.assertIn("git status --porcelain", script("setup").rstrip().splitlines()[-1])

    @skipUnless(shutil.which("fabro") or Path.home().joinpath(".fabro/bin/fabro").exists(), "fabro isn't installed, as in CI")
    def test_the_graph_is_valid(self):
        fabro = shutil.which("fabro") or str(Path.home() / ".fabro/bin/fabro")
        result = subprocess.run([fabro, "validate", str(BUILD / "workflow.fabro")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Validation: OK", result.stdout + result.stderr)


class BuildRouteTestCase(SimpleTestCase):
    """issue-builds: A stopped build skips the refactoring pass"""

    def test_routing_on_the_outcome(self):
        repo = Repo()
        self.addCleanup(repo.cleanup)
        for outcome, route in (("stopped", "finish"), ("complete", "refactor")):
            repo.record(outcome=outcome)
            result = repo.run("route")
            self.assertEqual(json.loads(result.stdout), {"context_updates": {"route": route}})


class BuildFinishTestCase(SimpleTestCase):
    """issue-builds: the final check, and the result it writes"""

    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.cleanup)

    def assert_fails(self, *words, suite="true"):
        result = self.repo.run("finish", suite)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for word in words:
            self.assertIn(word, result.stdout)
        self.assertFalse((self.repo.dir / ".intentable" / "result.json").exists())
        return result

    def test_a_clean_complete_build(self):
        self.repo.built(left=False)
        self.repo.record()
        result = self.repo.run("finish")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.repo.result()["outcome"], "complete")

    def test_a_merge_commit(self):
        self.repo.built(left=False)
        base = self.repo.git("rev-parse", "HEAD").strip()
        self.repo.git("checkout", "-q", "-b", "side", "HEAD~1")
        self.repo.commit("Side work", {"core/side.py": "X = 1\n"})
        self.repo.git("checkout", "-q", "change/" + CHANGE)
        self.repo.git("merge", "-q", "--no-ff", "-m", "Merge side", "side")
        merge = self.repo.git("rev-parse", "HEAD").strip()
        self.assertNotEqual(merge, base)
        self.repo.record()
        self.assert_fails(merge[:7], "merge")

    def test_work_left_uncommitted(self):
        self.repo.built(left=False)
        self.repo.commit("fabro(RUN1): apply (succeeded)", {"core/views.py": "LEFT = 1\n"})
        sha = self.repo.git("rev-parse", "HEAD").strip()
        self.repo.record()
        self.assert_fails(sha[:7], "checkpoint")

    def test_a_closing_keyword(self):
        for message in ("Add the export\n\nCloses: #3", "Add it\n\nfixes #3, fixes #4", "Resolve natea/x#3", "Close https://github.com/natea/newenglandmusic/issues/3", "Fixes\n#3"):
            with self.subTest(message=message):
                repo = Repo()
                self.addCleanup(repo.cleanup)
                repo.built(left=False)
                repo.commit(message, {"core/more.py": "Y = 1\n"})
                sha = repo.git("rev-parse", "HEAD").strip()
                repo.record()
                result = repo.run("finish")
                self.assertEqual(result.returncode, 1, message)
                self.assertIn(sha[:7], result.stdout)
        for message in ("Add a closed-venues filter", "Fix the #-less rows", "Prefix #3 stays"):
            with self.subTest(message=message):
                repo = Repo()
                self.addCleanup(repo.cleanup)
                repo.built(left=False)
                repo.commit(message, {"core/more.py": "Y = 1\n"})
                repo.record()
                self.assertEqual(repo.run("finish").returncode, 0, message)

    def test_a_protected_file(self):
        # the prompt is on the branch before the commit the run targeted; the build renames it
        self.repo.commit("Add the prompt", {".fabro/workflows/build/apply.md": "x\n"})
        self.repo.write(".intentable/start", self.repo.git("rev-parse", "HEAD").strip() + "\n")
        self.repo.built(left=False)
        (self.repo.dir / "notes").mkdir()
        self.repo.git("mv", ".fabro/workflows/build/apply.md", "notes/apply.md")
        self.repo.git("commit", "-q", "-m", "Move the prompt")
        sha = self.repo.git("rev-parse", "HEAD").strip()
        self.repo.record()
        self.assert_fails(sha[:7], ".fabro/workflows/build/apply.md")

    def test_an_unticked_box(self):
        self.repo.built(left=True)
        self.repo.record()
        self.assert_fails("task 2.2", "unticked")

    def test_nothing_built(self):
        self.repo.commit("fabro(RUN1): setup (succeeded)")
        self.repo.commit("fabro(RUN1): apply (succeeded)")
        self.repo.tick("1.1", "1.2", "2.1", "2.2")
        self.repo.git("add", "-A")
        self.repo.git("commit", "-q", "-m", "fabro(RUN1): refactor (succeeded)")
        # that last checkpoint holds the ticks, so drop it: only empty checkpoints remain
        self.repo.git("reset", "-q", "--hard", "HEAD~1")
        self.repo.record()
        self.assert_fails("made no commit")

    def test_a_task_left_for_a_person(self):
        self.repo.built(left=True)
        self.repo.record(left_for_people=[{"task": "2.2", "reason": "it needs a browser by hand"}], message="Built; task 2.2 is left for Nate.")
        result = self.repo.run("finish")
        self.assertEqual(result.returncode, 0, result.stdout)
        pull_request = (self.repo.dir / ".intentable" / "pull-request.md").read_text()
        self.assertIn("Task 2.2: it needs a browser by hand", pull_request)

    def test_a_listed_task_that_isnt_left(self):
        for task in ("1.1", "9.9"):
            with self.subTest(task=task):
                repo = Repo()
                self.addCleanup(repo.cleanup)
                repo.built(left=True)
                repo.record(left_for_people=[{"task": task, "reason": "x"}])
                result = repo.run("finish")
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"task {task} is listed as needing a person", result.stdout)

    def test_a_stopped_build_with_an_unfinished_group(self):
        self.repo.tick("1.1", "1.2")
        self.repo.commit("Add the venue export", {"core/export.py": "X = 1\n"})
        self.repo.record(outcome="stopped", message="Group 2's test fails on an empty venue list, so I stopped there.")
        result = self.repo.run("finish")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.repo.result()["outcome"], "stopped")

    def test_a_failing_suite(self):
        self.repo.built(left=False)
        self.repo.record()
        self.assert_fails("the suite fails", suite="false")

    def test_a_malformed_record(self):
        self.repo.built(left=False)
        self.repo.record(outcome="passed")
        self.assert_fails("complete or stopped")
        self.repo.record(change="add-venue-hours")
        self.assert_fails("no change folder")

    def test_no_record(self):
        self.repo.built(left=False)
        self.assert_fails("no record")

    def test_a_message_that_breaks_the_rules(self):
        self.repo.built(left=False)
        for message, words in (("  ", "empty"), ("x" * 2001, "2001 characters"), ("Thanks @sooz for asking.", "mentions someone")):
            with self.subTest(message=message[:20]):
                self.repo.record(message=message)
                self.assert_fails(words)

    def test_code_in_the_message(self):
        self.repo.built(left=False)
        self.repo.record(message="The export uses `@admin.register`, so it shows in the admin.")
        self.assertEqual(self.repo.run("finish").returncode, 0)

    def test_the_written_result(self):
        self.repo.built(left=False)
        self.repo.record(message="The venue list has an export button.")
        self.repo.write(".intentable/summary.md", "Adds an Export to CSV button.\n")
        result = self.repo.run("finish")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(
            self.repo.result(),
            {"labels": [], "state": None, "message": "The venue list has an export button.", "outcome": "complete", "change": CHANGE},
        )
        self.assertEqual((self.repo.dir / ".intentable" / "pull-request.md").read_text(), "Adds an Export to CSV button.\n")

    def test_no_summary(self):
        self.repo.built(left=False)
        self.repo.record()
        self.assertEqual(self.repo.run("finish").returncode, 0)
        self.assertFalse((self.repo.dir / ".intentable" / "pull-request.md").exists())
