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
    for match in re.finditer(r"^[ \t]*(\w+)[ \t]*\[", text, re.MULTILINE):
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
        for name, attrs in commands().items():
            self.assertNotRegex(attrs["script"], r"(?<![\w./-])bin/", f"{name} runs a script from the repository's bin/")

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
