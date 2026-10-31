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
