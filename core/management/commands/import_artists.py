from core.artist_import import COLUMNS, import_rows, rows_from_csv
from core.job_runs import RecordedCommand
from core.management.commands.sync_venues_from_gsheets import get_rows_from_google_sheets
from django.core.management.base import BaseCommand, CommandError

"""
imports artists and bands from a csv file or a google sheet tab, in the layout described in
core/artist_import.py, keyed by Act_ID.

run as:

python manage.py import_artists --csv path/to/acts.csv [--dry-run]
python manage.py import_artists --sheet <sheet id> --tab "Acts" [--dry-run]

a sheet is read as the venue sheet is: with the service account on a server
(GOOGLE_SERVICE_ACCOUNT_JSON), and with the gog cli otherwise. rows are created or updated;
nothing is deleted, and a field an editor or musicbrainz set is left alone. problems with a
row or a value are reported, and the rest is imported.
"""


class Command(RecordedCommand, BaseCommand):
    help = "import artists and bands from a csv file or a google sheet tab"

    def add_arguments(self, parser):
        parser.add_argument("--csv", help="a csv file in the layout")
        parser.add_argument("--sheet", help="a google sheet's id")
        parser.add_argument("--tab", help="the sheet's tab")
        parser.add_argument("--dry-run", action="store_true", help="report what would change, and save nothing")

    def handle(self, *args, **options):
        rows = self.read_rows(options)
        missing = [column for column in ("Act_ID", "Name", "Kind") if rows and column not in rows[0]]
        if missing:
            raise CommandError(f"missing columns: {', '.join(missing)} (the layout: {', '.join(COLUMNS)})")
        report = import_rows(rows, dry_run=options["dry_run"])
        self.job_summary = report.summary()
        self.print_report(report, options["dry_run"])

    def read_rows(self, options):
        if bool(options["csv"]) == bool(options["sheet"]):
            raise CommandError("give either --csv or --sheet (with --tab)")
        if options["csv"]:
            try:
                with open(options["csv"], newline="", encoding="utf-8-sig") as file:
                    return rows_from_csv(file)
            except OSError as e:
                raise CommandError(f"couldn't read {options['csv']}: {e.strerror}")
        if not options["tab"]:
            raise CommandError("--sheet needs --tab")
        return get_rows_from_google_sheets(options["sheet"], options["tab"])

    def print_report(self, report, dry_run):
        suffix = " [dry run, not saved]" if dry_run else ""
        for title, items in (("created", report.created), ("updated", report.updated), ("members added", report.members_added)):
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{title}{suffix} ({len(items)})"))
            for item in items:
                self.stdout.write(f"  {item}")
        self.stdout.write(f"\nunchanged ({len(report.unchanged)})")
        if report.problems:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\nproblems ({len(report.problems)})"))
            for number, act_id, problem in report.problems:
                self.stdout.write(self.style.WARNING(f"  row {number} {act_id}: {problem}"))
