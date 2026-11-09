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
