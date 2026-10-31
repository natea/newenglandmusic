import re
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
