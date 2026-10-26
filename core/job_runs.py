"""
recording each run of a pipeline command as a JobRun, so scheduled runs can be reviewed in
the admin (/admin/core/jobrun/) after the host's own logs are gone.

a command opts in by subclassing RecordedCommand ahead of BaseCommand, and can set
self.job_summary to a list of (label, count) pairs for the admin list, and
self.job_problems to the venues it had problems with (see JobRun.problems):

    class Command(RecordedCommand, BaseCommand):
        def handle(self, *args, **options):
            ...
            self.job_summary = [("created", nmb_created), ("updated", nmb_updated)]

the command prints exactly what it printed before, and recording is best-effort: if
saving the run fails, a warning goes to stderr and the command carries on.
"""

import datetime
import json
import re
import sys
import traceback
from io import StringIO

from core.models import JobRun
from django.utils import timezone

# a run still marked running after this long was killed (out of memory, a host timeout)
STALE_AFTER = datetime.timedelta(hours=6)
KEEP_FOR = datetime.timedelta(days=90)
# a stored report keeps its first and last OUTPUT_LIMIT / 2 characters
OUTPUT_LIMIT = 200_000

# options every django command has, which say nothing about the run
STANDARD_OPTIONS = {
    "verbosity",
    "settings",
    "pythonpath",
    "traceback",
    "no_color",
    "force_color",
    "skip_checks",
    "stdout",
    "stderr",
}

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

DIDNT_FINISH = "didn't finish"


def outcome(run, now=None):
    """the run's status for people: running, succeeded, failed or didn't finish"""
    if (
        run.status == JobRun.Status.RUNNING
        and run.started_at < (now or timezone.now()) - STALE_AFTER
    ):
        return DIDNT_FINISH
    return run.status


def clip(text, limit=None):
    limit = limit or OUTPUT_LIMIT
    if len(text) <= limit:
        return text
    half = limit // 2
    left_out = len(text) - 2 * half
    return (
        f"{text[:half]}\n\n[... {left_out:,} characters left out ...]\n\n{text[-half:]}"
    )


def run_arguments(args, options, defaults):
    """the options given, i.e. those that differ from their defaults"""
    arguments = {
        key: value
        for key, value in options.items()
        if key not in STANDARD_OPTIONS and value != defaults.get(key)
    }
    if args:
        arguments["args"] = list(args)
    # keep it storable as json whatever a command passes
    return json.loads(json.dumps(arguments, default=str))


class Tee:
    """writes to the command's real output and to a buffer"""

    def __init__(self, stream, buffer):
        self.stream = stream
        self.buffer = buffer

    def write(self, text):
        self.buffer.write(text)
        return self.stream.write(text)

    def flush(self):
        if hasattr(self.stream, "flush"):
            self.stream.flush()

    def isatty(self):
        # so django colours the output exactly as it would without recording
        return hasattr(self.stream, "isatty") and self.stream.isatty()


class RecordedCommand:
    job_summary = None
    job_problems = None

    def execute(self, *args, **options):
        captured = StringIO()
        options["stdout"] = Tee(options.get("stdout") or sys.stdout, captured)
        stderr = options.get("stderr") or sys.stderr
        self.job_summary = []
        self.job_problems = []
        self.job_run = run = self._start_run(args, options, stderr)
        try:
            result = super().execute(*args, **options)
        except BaseException:
            self._finish_run(
                run, JobRun.Status.FAILED, captured, stderr, traceback.format_exc()
            )
            raise
        self._finish_run(run, JobRun.Status.SUCCEEDED, captured, stderr)
        return result

    def command_name(self):
        return self.__module__.rsplit(".", 1)[-1]

    def option_defaults(self):
        parser = self.create_parser("manage.py", self.command_name())
        return {action.dest: action.default for action in parser._actions}

    def _start_run(self, args, options, stderr):
        try:
            now = timezone.now()
            JobRun.objects.filter(started_at__lt=now - KEEP_FOR).delete()
            return JobRun.objects.create(
                command=self.command_name(),
                arguments=run_arguments(args, options, self.option_defaults()),
                started_at=now,
                dry_run=bool(options.get("dry_run")),
            )
        except Exception as e:
            stderr.write(f"warning: couldn't record this run: {e}\n")
            return None

    def _finish_run(self, run, status, captured, stderr, error=""):
        if run is None:
            return
        try:
            run.status = status
            run.finished_at = timezone.now()
            run.summary = [[label, count] for label, count in (self.job_summary or [])]
            run.problems = self.job_problems or []
            run.output = clip(ANSI_RE.sub("", captured.getvalue()))
            run.error = error
            run.save()
        except Exception as e:
            stderr.write(f"warning: couldn't record the end of this run: {e}\n")
