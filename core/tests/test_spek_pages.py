import os
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
        self.assertEqual(data["permissions"], {})
        self.assertEqual(job["permissions"], {"contents": "write"})
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
        self.assertIn("github.repository == 'natea/newenglandmusic'", spek_workflow()[2]["if"])
        self.assertIn("github.repository == 'natea/newenglandmusic'", spek_workflow()[0]["jobs"]["thumbnails"]["if"])


class SpekWorkflowQueueTestCase(SimpleTestCase):
    """publishes queue, and never fail a commit's checks"""

    def test_one_at_a_time(self):
        self.assertEqual(
            spek_workflow()[0]["concurrency"], {"group": "spek-pages", "cancel-in-progress": False, "queue": "max"}
        )

    def test_a_failed_publish_doesnt_fail_the_commit(self):
        for name, job in spek_workflow()[0]["jobs"].items():
            for s in job["steps"]:
                self.assertIs(s.get("continue-on-error"), True, (name, s.get("name")))


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


SKETCH = "<!doctype html><html><head><title>A</title></head><body><p>hours</p></body></html>"
POLICY_START = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\';'


# stands in for Chrome in tests: records its arguments and writes what --screenshot names, or fails
FAKE_CHROME = """#!/bin/sh
[ -n "$FAKE_CHROME_FAILS" ] && exit 1
echo "$@" >> "$FAKE_CHROME_LOG"
for arg in "$@"; do
  case "$arg" in --screenshot=*) printf png > "${arg#--screenshot=}";; esac
done
"""


def publish_from(checkout, branch, site, thumbnails=None):
    """runs the script for a branch from a checkout folder, as the workflow does from the repo root"""
    with tempfile.TemporaryDirectory() as build:
        page = Path(build) / "spek.html"
        page.write_text("<html>new page</html>")
        args = [branch, str(page), str(site)] + ([str(thumbnails)] if thumbnails else [])
        return subprocess.run(
            [sys.executable, str(PUBLISH), *args], cwd=checkout, capture_output=True, text=True, timeout=30
        ).returncode


def render_from(checkout, branch, out, chrome="works"):
    """runs the thumbnail job's command; PATH holds no browser but the fake one; returns (status, Chrome's arguments)"""
    with tempfile.TemporaryDirectory() as build:
        log = Path(build) / "chrome.log"
        env = {**os.environ, "PATH": build, "FAKE_CHROME_LOG": str(log)}
        if chrome:
            fake = Path(build) / "google-chrome"
            fake.write_text(FAKE_CHROME.replace("#!/bin/sh", f"#!/bin/sh\nPATH={os.environ['PATH']}"))
            fake.chmod(0o755)
            if chrome == "fails":
                env["FAKE_CHROME_FAILS"] = "1"
        done = subprocess.run(
            [sys.executable, str(PUBLISH), "--thumbnails", branch, str(out)],
            cwd=checkout,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        return done.returncode, log.read_text() if log.exists() else ""


def checkout_with_sketches(folder, name="add-venue-hours", sketches=("a.html", "b.html", "c.html"), text=SKETCH):
    root = Path(folder) / "checkout"
    sketch_dir = root / "openspec" / "changes" / name / "sketches"
    sketch_dir.mkdir(parents=True)
    for sketch in sketches:
        (sketch_dir / sketch).write_text(text)
    (sketch_dir / "options.json").write_text("[]")
    return root


class SketchPagesTestCase(SimpleTestCase):
    """a change's sketches are published beside its page; published sketches can't run code or call out"""

    def test_sketches_published(self):
        with tempfile.TemporaryDirectory() as folder:
            checkout = checkout_with_sketches(folder)
            site = Path(folder) / "site"
            other = site / "changes" / "add-other" / "index.html"
            other.parent.mkdir(parents=True)
            other.write_text("<html>other</html>")
            self.assertEqual(publish_from(checkout, "change/add-venue-hours", site), 0)
            published = files_in(site)
            for sketch in ("a.html", "b.html", "c.html"):
                self.assertIn(f"changes/add-venue-hours/sketches/{sketch}", published)
            self.assertNotIn("changes/add-venue-hours/sketches/options.json", published)
            self.assertIn("changes/add-venue-hours/index.html", published)
            self.assertEqual(published["changes/add-other/index.html"], "<html>other</html>")

    def test_a_sketch_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            checkout = checkout_with_sketches(folder, sketches=("a.html", "b.html"))
            site = Path(folder) / "site"
            stale = site / "changes" / "add-venue-hours" / "sketches" / "c.html"
            stale.parent.mkdir(parents=True)
            stale.write_text(SKETCH)
            self.assertEqual(publish_from(checkout, "change/add-venue-hours", site), 0)
            self.assertFalse(stale.exists())

    def test_a_link_instead_of_a_file(self):
        with tempfile.TemporaryDirectory() as folder:
            checkout = checkout_with_sketches(folder, sketches=("b.html",))
            secret = Path(folder) / "secret.txt"
            secret.write_text("token")
            (checkout / "openspec" / "changes" / "add-venue-hours" / "sketches" / "a.html").symlink_to(secret)
            site = Path(folder) / "site"
            self.assertEqual(publish_from(checkout, "change/add-venue-hours", site), 0)
            published = files_in(site)
            self.assertNotIn("changes/add-venue-hours/sketches/a.html", published)
            self.assertIn("changes/add-venue-hours/sketches/b.html", published)

    def test_policy_added(self):
        with tempfile.TemporaryDirectory() as folder:
            checkout = checkout_with_sketches(folder, sketches=("a.html",))
            site = Path(folder) / "site"
            publish_from(checkout, "change/add-venue-hours", site)
            text = (site / "changes" / "add-venue-hours" / "sketches" / "a.html").read_text()
            self.assertTrue(text.startswith("<!doctype html>" + POLICY_START))
            self.assertIn("img-src data:; form-action 'none'; base-uri 'none'", text)
            self.assertTrue(text.endswith(SKETCH[len("<!doctype html>") :]))

    def test_a_sketch_with_no_head(self):
        with tempfile.TemporaryDirectory() as folder:
            checkout = checkout_with_sketches(folder, sketches=("a.html",), text="<script>go()</script><p>x</p>")
            site = Path(folder) / "site"
            publish_from(checkout, "change/add-venue-hours", site)
            text = (site / "changes" / "add-venue-hours" / "sketches" / "a.html").read_text()
            self.assertTrue(text.startswith(POLICY_START))
            self.assertLess(text.index("Content-Security-Policy"), text.index("<script>"))

    def test_no_sketches_on_main(self):
        with tempfile.TemporaryDirectory() as folder:
            checkout = checkout_with_sketches(folder)
            site = Path(folder) / "site"
            self.assertEqual(publish_from(checkout, "main", site), 0)
            self.assertFalse([p for p in site.rglob("sketches")])

    def test_thumbnails_made(self):
        with tempfile.TemporaryDirectory() as folder:
            checkout = checkout_with_sketches(folder)
            out = Path(folder) / "thumbs"
            status, chrome = render_from(checkout, "change/add-venue-hours", out)
            self.assertEqual(status, 0)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["a.png", "b.png", "c.png"])
            self.assertIn("--host-resolver-rules=MAP * ~NOTFOUND", chrome)
            site = Path(folder) / "site"
            self.assertEqual(publish_from(checkout, "change/add-venue-hours", site, out), 0)
            for sketch in ("a", "b", "c"):
                self.assertEqual(
                    (site / "changes" / "add-venue-hours" / "sketches" / f"{sketch}.png").read_text(), "png"
                )

    def test_a_thumbnail_that_cant_be_made(self):
        for chrome in (None, "fails"):
            with tempfile.TemporaryDirectory() as folder:
                checkout = checkout_with_sketches(folder)
                out = Path(folder) / "thumbs"
                self.assertEqual(render_from(checkout, "change/add-venue-hours", out, chrome=chrome)[0], 0, chrome)
                site = Path(folder) / "site"
                self.assertEqual(publish_from(checkout, "change/add-venue-hours", site, out), 0, chrome)
                sketches = site / "changes" / "add-venue-hours" / "sketches"
                self.assertTrue((sketches / "a.html").is_file(), chrome)
                self.assertFalse((sketches / "a.png").exists(), chrome)

    def test_thumbnails_rendered_apart(self):
        data = spek_workflow()[0]
        job = data["jobs"]["thumbnails"]
        self.assertEqual(job["permissions"], {"contents": "read"})
        checkout = next(s for s in job["steps"] if s.get("id") == "checkout")
        self.assertIs(checkout["with"]["persist-credentials"], False)
        self.assertEqual(data["jobs"]["publish"]["needs"], "thumbnails")
        for s in data["jobs"]["publish"]["steps"]:
            self.assertNotIn("--thumbnails", s.get("run", ""))

    def test_a_sketch_with_http_equiv(self):
        with tempfile.TemporaryDirectory() as folder:
            refresh = '<!doctype html><!--><meta http-equiv=refresh content="0;url=https://x.example/">-->'
            checkout = checkout_with_sketches(folder, sketches=("a.html",), text=refresh)
            (checkout / "openspec" / "changes" / "add-venue-hours" / "sketches" / "b.html").write_text(SKETCH)
            site = Path(folder) / "site"
            out = Path(folder) / "thumbs"
            _, chrome = render_from(checkout, "change/add-venue-hours", out)
            self.assertEqual(publish_from(checkout, "change/add-venue-hours", site), 0)
            sketches = site / "changes" / "add-venue-hours" / "sketches"
            self.assertFalse((sketches / "a.html").exists())
            self.assertTrue((sketches / "b.html").is_file())
            self.assertNotIn("a.png", chrome)
