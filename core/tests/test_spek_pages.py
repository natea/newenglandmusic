import subprocess
import sys
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]
PUBLISH = ROOT / "bin" / "publish-spek-page"


def files_in(folder):
    """every file under a folder, as relative paths with their contents"""
    return {str(p.relative_to(folder)): p.read_text() for p in sorted(folder.rglob("*")) if p.is_file()}


def publish(branch, site, html="<html>new page</html>"):
    """runs the script for a branch into a site folder; returns its exit status"""
    with tempfile.TemporaryDirectory() as build:
        page = Path(build) / "spek.html"
        page.write_text(html)
        return subprocess.run(
            [sys.executable, str(PUBLISH), branch, str(page), str(site)], capture_output=True, text=True, timeout=30
        ).returncode


class PlacingAPageTestCase(SimpleTestCase):
    """main's specs at the site root; each change branch its own page"""

    def test_the_main_page(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            change = site / "changes" / "add-triage-clarify" / "index.html"
            change.parent.mkdir(parents=True)
            change.write_text("<html>triage page</html>")
            (site / "index.html").write_text("<html>old root</html>")
            self.assertEqual(publish("main", site), 0)
            self.assertEqual(
                files_in(site),
                {
                    ".nojekyll": "",
                    "changes/add-triage-clarify/index.html": "<html>triage page</html>",
                    "index.html": "<html>new page</html>",
                },
            )

    def test_a_change_page(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            (site / "index.html").write_text("<html>root</html>")
            self.assertEqual(publish("change/add-triage-clarify", site), 0)
            self.assertEqual(
                files_in(site),
                {
                    ".nojekyll": "",
                    "changes/add-triage-clarify/index.html": "<html>new page</html>",
                    "index.html": "<html>root</html>",
                },
            )

    def test_branches_that_get_no_page(self):
        for branch in ("fabro-setup", "change/a/b", "change/.hidden", "change/$(id)", "change/", "change/-x"):
            with tempfile.TemporaryDirectory() as folder:
                site = Path(folder)
                self.assertNotEqual(publish(branch, site), 0, branch)
                self.assertEqual(files_in(site), {}, branch)
