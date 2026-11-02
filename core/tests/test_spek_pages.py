import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
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


WORKFLOW = ROOT / ".github" / "workflows" / "spek.yml"
SPEK_COMMIT = "5542fa2dfda6c52a08fb0610a140670052056c66"


def spek_workflow():
    """the workflow's triggers, and its one job; PyYAML reads the bare `on:` key as True"""
    data = yaml.safe_load(WORKFLOW.read_text())
    return data, data[True], data["jobs"]["publish"]


def step(job, step_id):
    return next(s for s in job["steps"] if s.get("id") == step_id)


def publish_step(job):
    return next(s for s in job["steps"] if "run" in s)


class SpekWorkflowTriggersTestCase(SimpleTestCase):
    """when the Spek workflow runs"""

    def test_mains_trigger(self):
        triggers = spek_workflow()[1]
        self.assertIn("schedule", triggers)
        self.assertEqual(len(triggers["schedule"]), 1)
        self.assertIn("workflow_dispatch", triggers)
        self.assertNotIn("main", triggers["push"]["branches"])

    def test_change_branches_trigger(self):
        push = spek_workflow()[1]["push"]
        self.assertEqual(push["branches"], ["change/*"])
        self.assertEqual(push["paths"], ["openspec/**", ".github/workflows/spek.yml"])

    def test_no_removal_on_delete(self):
        data, triggers, job = spek_workflow()
        self.assertNotIn("delete", triggers)
        for s in job["steps"]:
            self.assertNotRegex(s.get("run", ""), r"\b(rm|git rm)\b")


class SpekWorkflowSafetyTestCase(SimpleTestCase):
    """the build is pinned and least-privileged; a failure can't wipe the pages"""

    def test_a_failure_cant_wipe_the_pages(self):
        job = spek_workflow()[2]
        publish_ = publish_step(job)
        self.assertEqual(publish_["if"], "steps.build.outcome == 'success'")
        self.assertEqual(step(job, "build")["uses"].split("@")[0], "spekhq/spek")
        script = publish_["run"]
        self.assertTrue(script.lstrip().startswith("set -euo pipefail"))
        self.assertIn("git ls-remote --exit-code --heads origin gh-pages >/dev/null || rc=$?", script)
        self.assertIn('if [ "$rc" -eq 2 ]; then', script)
        self.assertIn('lease="gh-pages:"', script)
        self.assertIn('lease="gh-pages:$fetched"', script)
        self.assertIn('--force-with-lease="$lease"', script)

    def test_pinned_and_narrow(self):
        data, triggers, job = spek_workflow()
        build = step(job, "build")
        self.assertEqual(build["uses"], f"spekhq/spek@{SPEK_COMMIT}")
        self.assertEqual(build["with"]["spek-version"], SPEK_COMMIT)
        self.assertEqual(step(job, "checkout")["with"]["fetch-depth"], 0)
        self.assertEqual(data["permissions"], {"contents": "write"})
        script = publish_step(job)["run"]
        pushes = [line for line in script.splitlines() if " push " in line]
        self.assertEqual(len(pushes), 1)
        self.assertIn("HEAD:refs/heads/gh-pages", pushes[0])
        for s in job["steps"]:
            self.assertNotIn("${{ github.ref", s.get("run", ""))
            self.assertNotIn("${{ github.event", s.get("run", ""))
        self.assertEqual(publish_step(job)["env"]["BRANCH"], "${{ github.ref_name }}")

    def test_never_upstream(self):
        self.assertNotIn("nycnoise/nycnoise", WORKFLOW.read_text())
        self.assertEqual(spek_workflow()[2]["if"], "github.repository == 'natea/newenglandmusic'")


class SpekWorkflowQueueTestCase(SimpleTestCase):
    """publishes queue, and never fail a commit's checks"""

    def test_one_at_a_time(self):
        self.assertEqual(
            spek_workflow()[0]["concurrency"], {"group": "spek-pages", "cancel-in-progress": False, "queue": "max"}
        )

    def test_a_failed_publish_doesnt_fail_the_commit(self):
        for s in spek_workflow()[2]["steps"]:
            self.assertIs(s.get("continue-on-error"), True, s.get("name"))


class RuleAndGuideTestCase(SimpleTestCase):
    """drafts published before the owner confirms them; a guide says where the pages are"""

    def test_the_rule_is_written_down(self):
        agents = (ROOT / "AGENTS.md").read_text()
        for needed in (
            "G2 is the owner confirming a proposal",
            '"Draft" in the commit subject',
            '"Confirm proposal <name> (G2)"',
            "https://natea.github.io/newenglandmusic/changes/<name>/",
            "`change/<name>` branches may be pushed here without asking",
            "push `main` only when asked",
            "Keep host and network names out of OpenSpec files",
        ):
            self.assertIn(needed, agents)

    def test_guide_addresses(self):
        guide = (ROOT / "docs" / "SPEK.md").read_text()
        for needed in (
            "https://natea.github.io/newenglandmusic/",
            "https://natea.github.io/newenglandmusic/changes/<name>/",
            "`.github/workflows/spek.yml`",
            "whole repository's OpenSpec",
            "Pages stay after a branch is deleted",
            "Keep host and network names out of OpenSpec files",
        ):
            self.assertIn(needed, guide)
