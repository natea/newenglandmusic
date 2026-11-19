"""preview-environments: the nightly copy's script and the two workflows, read as files"""

import os
import stat
import subprocess
import tempfile
from pathlib import Path

import yaml
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

# stands in for psql, pg_dump, pg_restore and python: records each call without its
# addresses' secrets, answers the role check, and fails the step named in $FAIL_STEP
STUB = """#!/usr/bin/env bash
name=$(basename "$0")
echo "$name $*" | tr '\\n' ' ' >> "$CALLS"; echo >> "$CALLS"
if [ "$name" = psql ]; then echo "$ROLE_ANSWER"; fi
if [ "$name" = python ] && [ "$1" = -c ]; then echo "--exclude-table-data=public.core_subscriber"; fi
case "$name $*" in *"$FAIL_STEP"*) [ -n "$FAIL_STEP" ] && exit 3;; esac
exit 0
"""


def workflow(name):
    data = yaml.safe_load((WORKFLOWS / name).read_text())
    # yaml reads the key `on` as True
    data["on"] = data.pop(True)
    return data


class BaseCopyTestCase(SimpleTestCase):
    """A cleaned copy of the live data is kept for previews"""

    def run_copy(self, role_answer="preview_reader f", fail_step=""):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("psql", "pg_dump", "pg_restore", "python"):
                stub = Path(tmp) / name
                stub.write_text(STUB)
                stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
            calls = Path(tmp) / "calls"
            calls.touch()
            env = {
                **os.environ,
                "PATH": f"{tmp}:{os.environ['PATH']}",
                "CALLS": str(calls),
                "ROLE_ANSWER": role_answer,
                "FAIL_STEP": fail_step,
                "PREVIEW_SOURCE_DATABASE_URL": "postgres://live",
                "SCRATCH_DATABASE_URL": "postgres://scratch",
                "NEON_BASE_URL": "postgres://base",
            }
            result = subprocess.run(["bash", str(ROOT / "bin" / "preview-base")], env=env, capture_output=True, text=True, timeout=30)
            return result, calls.read_text().splitlines()

    def test_the_nightly_copy(self):
        result, calls = self.run_copy()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        steps = [" ".join(c.split()[:1] + [w for w in c.split()[1:] if w.startswith("postgres://") or w in ("migrate", "scrub_preview_data", "--single-transaction")]) for c in calls]
        self.assertEqual(
            steps,
            [
                "psql postgres://live",
                "python",
                "pg_dump postgres://live",
                "pg_restore postgres://scratch",
                "python migrate",
                "python scrub_preview_data",
                "pg_dump postgres://scratch",
                "pg_restore --single-transaction postgres://base",
            ],
        )
        self.assertIn("--exclude-table-data=public.core_subscriber", calls[2])
        self.assertNotIn("postgres://", result.stdout + result.stderr)

    def test_the_copy_fails(self):
        result, calls = self.run_copy(fail_step="pg_dump --format=custom --no-owner --no-privileges --exclude")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("postgres://base" in c for c in calls))

    def test_a_role_that_can_write(self):
        result, calls = self.run_copy(role_answer="newenglandmusic_user t")
        self.assertEqual(result.returncode, 1)
        self.assertIn("newenglandmusic_user may write to the live database", result.stdout)
        self.assertEqual(len(calls), 1)

    def test_cleaned_before_it_is_stored(self):
        result, calls = self.run_copy(fail_step="scrub_preview_data")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("postgres://base" in c for c in calls))

    def test_the_scrub_runs_under_the_preview_settings_on_the_scratch_copy(self):
        script = (ROOT / "bin" / "preview-base").read_text()
        self.assertIn("DJANGO_SETTINGS_MODULE=nycnoise.settings.preview", script)
        self.assertIn('DATABASE_URL="$SCRATCH_DATABASE_URL" python manage.py scrub_preview_data', script)
        self.assertIn("trap 'rm -rf \"$work\"' EXIT", script)


class BaseWorkflowTestCase(SimpleTestCase):
    def setUp(self):
        self.workflow = workflow("preview-base.yml")

    def test_nightly_and_by_hand(self):
        self.assertEqual(self.workflow["on"]["schedule"], [{"cron": "30 8 * * *"}])
        self.assertIn("workflow_dispatch", self.workflow["on"])
        self.assertNotIn("pull_request", self.workflow["on"])

    def test_only_the_copy_reads_the_live_database(self):
        jobs = self.workflow["jobs"]
        self.assertEqual(jobs["copy"]["environment"], "preview-base")
        self.assertNotIn("environment", jobs["sweep"])
        self.assertNotIn("PREVIEW_SOURCE_DATABASE_URL", str(jobs["sweep"]))
        # the copy never signs in to google cloud, and holds no write to the repository
        self.assertNotIn("google-github-actions/auth", str(jobs["copy"]))
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})

    def test_this_repository_only(self):
        for job in self.workflow["jobs"].values():
            self.assertIn("github.repository == 'natea/newenglandmusic'", job["if"])

    def test_the_sweep_runs_after_the_copy_however_it_went(self):
        sweep = self.workflow["jobs"]["sweep"]
        self.assertEqual(sweep["needs"], "copy")
        self.assertIn("always()", sweep["if"])
        self.assertEqual(sweep["permissions"]["deployments"], "write")

    def test_postgres_17(self):
        copy = self.workflow["jobs"]["copy"]
        self.assertEqual(copy["services"]["postgres"]["image"], "postgres:17")
        self.assertIn("postgresql-client-17", str(copy["steps"]))


class PreviewWorkflowTestCase(SimpleTestCase):
    def setUp(self):
        self.workflow = workflow("preview.yml")
        self.text = (WORKFLOWS / "preview.yml").read_text()

    def test_triggers(self):
        on = self.workflow["on"]
        self.assertEqual(on["pull_request"], {"types": ["opened", "synchronize", "reopened", "closed"], "branches": ["main"]})
        self.assertTrue(on["workflow_dispatch"]["inputs"]["pull_request"]["required"])
        # every pull request reaches bin/preview, which decides: a spec-only one gains a preview with its first code
        self.assertNotIn("paths-ignore", on["pull_request"])

    def test_no_forks_no_dependabot_and_this_repository_only(self):
        deploy, closed = self.workflow["jobs"]["deploy"]["if"], self.workflow["jobs"]["closed"]["if"]
        for condition in (deploy, closed):
            self.assertIn("github.repository == 'natea/newenglandmusic'", condition)
            self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", condition)
        self.assertIn("github.event.pull_request.user.login != 'dependabot[bot]'", deploy)
        self.assertIn("github.event.action != 'closed'", deploy)
        self.assertIn("github.event.action == 'closed'", closed)

    def test_one_run_at_a_time_for_each_pull_request(self):
        self.assertEqual(self.workflow["concurrency"]["cancel-in-progress"], False)
        self.assertIn("github.event.pull_request.number || inputs.pull_request", self.workflow["concurrency"]["group"])

    def test_permissions(self):
        self.assertEqual(self.workflow["permissions"], {"contents": "read", "id-token": "write", "deployments": "write", "pull-requests": "read"})

    def test_it_never_names_the_live_database(self):
        self.assertNotIn("preview-base", self.text.split("on:", 1)[1])
        self.assertNotIn("PREVIEW_SOURCE_DATABASE_URL", self.text)
        for job in self.workflow["jobs"].values():
            self.assertNotIn("environment", job)

    def test_a_closed_pull_request_runs_mains_script(self):
        checkout = self.workflow["jobs"]["closed"]["steps"][0]
        self.assertEqual(checkout["with"]["ref"], "main")

    def test_no_secret_on_a_command_line(self):
        for job in self.workflow["jobs"].values():
            for step in job["steps"]:
                self.assertNotIn("secrets.", step.get("run", ""))

    def test_the_same_previews_in_both_workflows(self):
        self.assertEqual(
            {k: v for k, v in self.workflow["env"].items() if k != "NUMBER"},
            workflow("preview-base.yml")["env"],
        )
