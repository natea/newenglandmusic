import datetime
from io import StringIO
from unittest import mock

from core import job_runs
from core.job_runs import RecordedCommand, clip, outcome
from core.models import JobRun
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.test import TestCase
from django.utils import timezone


class SampleCommand(RecordedCommand, BaseCommand):
    """a stand-in pipeline command"""

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--lines", type=int, default=1)
        parser.add_argument("--fail", action="store_true")

    def handle(self, *args, **options):
        for i in range(options["lines"]):
            self.stdout.write(f"line {i}")
        self.stdout.write(self.style.SUCCESS("done"))
        if options["fail"]:
            raise CommandError("it broke")
        self.job_summary = [("created", 2), ("updated", 3)]

    def command_name(self):
        return "sample"


def run_sample(*args):
    out = StringIO()
    call_command(SampleCommand(), *args, stdout=out, stderr=StringIO(), no_color=True)
    return out.getvalue()


class RecordedCommandTestCase(TestCase):
    def test_successful_run(self):
        output = run_sample("--lines", "2")
        run = JobRun.objects.get()
        self.assertEqual(run.command, "sample")
        self.assertEqual(run.status, JobRun.Status.SUCCEEDED)
        self.assertIsNotNone(run.finished_at)
        self.assertEqual(run.arguments, {"lines": 2})
        self.assertEqual(run.summary, [["created", 2], ["updated", 3]])
        self.assertEqual(run.output, output)
        self.assertEqual(output, "line 0\nline 1\ndone\n")

    def test_dry_run(self):
        run_sample("--dry-run")
        self.assertTrue(JobRun.objects.get().dry_run)

    def test_failure_is_recorded_and_reraised(self):
        with self.assertRaisesMessage(CommandError, "it broke"):
            run_sample("--fail")
        run = JobRun.objects.get()
        self.assertEqual(run.status, JobRun.Status.FAILED)
        self.assertIn("it broke", run.error)
        self.assertIn("done", run.output)

    def test_very_long_report(self):
        with mock.patch.object(job_runs, "OUTPUT_LIMIT", 100):
            run_sample("--lines", "50")
        run = JobRun.objects.get()
        self.assertTrue(run.output.startswith("line 0\n"))
        self.assertTrue(run.output.rstrip().endswith("done"))
        self.assertIn("characters left out", run.output)

    def test_clip(self):
        self.assertEqual(clip("short", limit=10), "short")
        clipped = clip("a" * 10 + "b" * 10, limit=10)
        self.assertTrue(clipped.startswith("aaaaa") and clipped.endswith("bbbbb"))
        self.assertIn("10 characters left out", clipped)

    def test_pruning(self):
        now = timezone.now()
        old = JobRun.objects.create(
            command="sample", started_at=now - datetime.timedelta(days=100)
        )
        recent = JobRun.objects.create(
            command="sample", started_at=now - datetime.timedelta(days=10)
        )
        run_sample()
        self.assertFalse(JobRun.objects.filter(pk=old.pk).exists())
        self.assertTrue(JobRun.objects.filter(pk=recent.pk).exists())

    def test_recording_error_doesnt_break_the_command(self):
        stderr = StringIO()
        out = StringIO()
        with mock.patch.object(
            JobRun.objects, "create", side_effect=RuntimeError("db down")
        ):
            call_command(SampleCommand(), stdout=out, stderr=stderr, no_color=True)
        self.assertEqual(out.getvalue(), "line 0\ndone\n")
        self.assertIn("couldn't record this run", stderr.getvalue())
        self.assertFalse(JobRun.objects.exists())

    def test_outcome(self):
        now = timezone.now()
        killed = JobRun(status="running", started_at=now - datetime.timedelta(hours=7))
        running = JobRun(
            status="running", started_at=now - datetime.timedelta(minutes=10)
        )
        failed = JobRun(status="failed", started_at=now - datetime.timedelta(hours=7))
        self.assertEqual(outcome(killed, now), "didn't finish")
        self.assertEqual(outcome(running, now), "running")
        self.assertEqual(outcome(failed, now), "failed")
