import json
import os
import re
import subprocess
import tempfile
import tomllib
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]
FABRO = ROOT / ".fabro"
UPSTREAM = "nycnoise/nycnoise"


def read_toml(path):
    with open(path, "rb") as f:
        return tomllib.load(f)


class ForkTargetTestCase(SimpleTestCase):
    """every Fabro run targets the fork, never the upstream repository"""

    def test_project_names_the_fork(self):
        scm = read_toml(FABRO / "project.toml")["run"]["scm"]
        self.assertEqual(scm, {"provider": "github", "owner": "natea", "repository": "newenglandmusic"})

    def test_no_setting_names_upstream(self):
        for path in FABRO.rglob("*"):
            if path.is_file():
                self.assertNotIn(UPSTREAM, path.read_text(), f"{path.relative_to(ROOT)} names the upstream repository")


def workflow(name):
    """a workflow's settings and its graph's steps, other than start and exit"""
    folder = FABRO / "workflows" / name
    graph = (folder / "workflow.fabro").read_text()
    steps = {
        node: attrs
        for node, attrs in re.findall(r"^\s*(\w+)\s*\[(.*?)\]\s*$", graph, re.MULTILINE | re.DOTALL)
        if node not in ("graph", "start", "exit")
    }
    edges = re.findall(r"^\s*start\s*->(.*?)->\s*exit\s*$", graph, re.MULTILINE)
    return read_toml(folder / "workflow.toml"), graph, steps, edges


class SmokeTestSettingsTestCase(SimpleTestCase):
    """the smoke-test workflows push nothing and open no pull request"""

    def assert_pushes_nothing(self, name):
        settings = workflow(name)[0]["run"]
        self.assertIs(settings["pull_request"]["enabled"], False)
        self.assertIs(settings["run_branch"]["push"], False)

    def test_hello(self):
        self.assert_pushes_nothing("hello")

    def test_claude_max(self):
        self.assert_pushes_nothing("claude-max")


class HelloWorkflowTestCase(SimpleTestCase):
    """hello checks the setup with one shell command and no model"""

    def test_one_command_step_and_no_model(self):
        settings, graph, steps, edges = workflow("hello")
        self.assertEqual(len(steps), 1)
        self.assertEqual(len(edges), 1)
        attrs = next(iter(steps.values()))
        self.assertIn("script=", attrs)
        self.assertNotIn("prompt=", attrs)
        self.assertNotRegex(graph, r"\b(model|provider|backend)\s*=")
        self.assertNotIn("model", settings.get("run", {}))


# a Claude subscription token or API key: sk-ant-, a token type, a hyphen, the key
TOKEN = re.compile(r"sk-ant-[a-z]+[0-9]*-[A-Za-z0-9_-]{20,}")


def daytona():
    return json.loads((FABRO / "environments" / "daytona.json").read_text())


class SubscriptionTokenTestCase(SimpleTestCase):
    """Claude Code signs in with the vault's subscription token, never an API key"""

    def test_token_comes_from_the_vault(self):
        env = daytona()["env"]
        self.assertEqual(env["CLAUDE_CODE_OAUTH_TOKEN"], "{{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}")
        self.assertEqual(env["ANTHROPIC_API_KEY"], "")
        others = {k: v for k, v in env.items() if k not in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")}
        self.assertFalse([k for k in others if "ANTHROPIC" in k or "CLAUDE" in k], others)

    def test_no_token_in_the_repo(self):
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
        for name in tracked.decode().split("\0"):
            path = ROOT / name
            if name and path.is_file():
                self.assertIsNone(TOKEN.search(path.read_text(errors="ignore")), f"{name} contains a token")


class SandboxLifecycleTestCase(SimpleTestCase):
    """smoke-test sandboxes stop when the run ends or after 30 idle minutes"""

    def test_lifecycle_settings(self):
        lifecycle = daytona()["lifecycle"]
        self.assertIs(lifecycle["preserve"], False)
        self.assertIs(lifecycle["stop_on_terminal"], True)
        minutes = re.fullmatch(r"(\d+)m", lifecycle["auto_stop"])
        self.assertTrue(minutes and 0 < int(minutes.group(1)) <= 30, lifecycle["auto_stop"])


class ClaudeMaxWorkflowTestCase(SimpleTestCase):
    """claude-max runs one Claude Code step through ACP in the daytona sandbox"""

    def test_one_acp_claude_code_step(self):
        settings, graph, steps, edges = workflow("claude-max")
        self.assertEqual(len(steps), 1)
        self.assertEqual(len(edges), 1)
        attrs = next(iter(steps.values()))
        self.assertIn('type="agent"', attrs)
        self.assertIn('backend="acp"', attrs)
        self.assertIn('acp.command="claude-code-acp"', attrs)
        self.assertIn("hello-claude-max.txt", attrs)
        self.assertEqual(daytona()["id"], "daytona")
        self.assertEqual(daytona()["provider"], "daytona")


# stands in for curl: records each call's arguments and request body, and answers the
# environment lookup with $LOOKUP_STATUS and an ETag of $REVISION
STUB_CURL = r"""#!/usr/bin/env bash
printf '%s\n' "$*" >> "$CALLS"
out=""; headers=""; body=""; prev=""
for arg in "$@"; do
  case "$prev" in
    -o) out="$arg" ;;
    -D) headers="$arg" ;;
    --data-binary) body="${arg#@}" ;;
    -H) case "$arg" in @*) cat "${arg#@}" >> "$SENT_HEADERS" ;; esac ;;
  esac
  prev="$arg"
done
if [ -n "$body" ]; then cp "$body" "$CALLS.body"; fi
if [ -n "$headers" ]; then
  printf 'HTTP/1.1 %s\r\nETag: %s\r\n\r\n' "$LOOKUP_STATUS" "$REVISION" > "$headers"
  echo '{}' > "$out"
  printf '%s' "$LOOKUP_STATUS"
fi
"""


class EnvironmentScriptTestCase(SimpleTestCase):
    """bin/fabro-environment puts the repo's environment on the Fabro server"""

    TOKEN = "test-dev-token-0123456789"

    def run_script(self, lookup_status):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            stub = tmp / "curl"
            stub.write_text(STUB_CURL)
            stub.chmod(0o755)
            env = {
                **os.environ,
                "PATH": f"{tmp}:{os.environ['PATH']}",
                "CALLS": str(tmp / "calls"),
                "SENT_HEADERS": str(tmp / "headers"),
                "LOOKUP_STATUS": lookup_status,
                "REVISION": '"rev-7"',
                "FABRO_DEV_TOKEN": self.TOKEN,
                "FABRO_SERVER": "http://fabro.test",
            }
            result = subprocess.run(
                [str(ROOT / "bin" / "fabro-environment")], env=env, capture_output=True, text=True
            )
            calls = (tmp / "calls").read_text().splitlines()
            body = json.loads((tmp / "calls.body").read_text()) if (tmp / "calls.body").exists() else None
            return result, calls, body, (tmp / "headers").read_text()

    def test_creates_the_environment_when_missing(self):
        result, calls, body, _ = self.run_script("404")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 2)
        self.assertIn("-X POST", calls[1])
        self.assertTrue(calls[1].endswith("http://fabro.test/api/v1/environments"))
        self.assertEqual(body, daytona())

    def test_replaces_the_environment_with_its_revision(self):
        result, calls, body, _ = self.run_script("200")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(calls), 2)
        self.assertIn("-X PUT", calls[1])
        self.assertIn('If-Match: "rev-7"', calls[1])
        self.assertTrue(calls[1].endswith("http://fabro.test/api/v1/environments/daytona"))
        expected = daytona()
        del expected["id"]
        self.assertEqual(body, expected)

    def test_dev_token_stays_off_command_lines(self):
        for status in ("404", "200"):
            result, calls, _, headers = self.run_script(status)
            self.assertIn(f"Authorization: Bearer {self.TOKEN}", headers)
            for call in calls:
                self.assertNotIn(self.TOKEN, call)
            self.assertNotIn(self.TOKEN, result.stdout + result.stderr)
