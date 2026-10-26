import csv
import datetime
import os

from core.event_sources import save_event_source
from core.models import Venue, VenueEventSource
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

"""
loads an event_sources.csv written by an older check_event_sources into the database
(VenueEventSource), so venues already checked don't have to be crawled again -- e.g.
before copying the local database to a server.

run as:

python manage.py import_event_sources event_sources.csv [--dry-run]

rows are matched to venues by sheet_id; rows for unknown venues are skipped. the results
are marked as checked when the file was last modified, so a later check shows as newer.
"""


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "path", help="the csv written by check_event_sources --output"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="report what would change, but save nothing",
        )

    def handle(self, *args, **options):
        path = options["path"]
        try:
            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
        except FileNotFoundError:
            raise CommandError(f"{path} not found")

        checked_at = datetime.datetime.fromtimestamp(
            os.path.getmtime(path), tz=datetime.timezone.utc
        )
        venues = Venue.objects.in_bulk(
            [row["sheet_id"] for row in rows if row.get("sheet_id")],
            field_name="sheet_id",
        )
        already_saved = set(
            VenueEventSource.objects.filter(venue__in=venues.values()).values_list(
                "venue_id", flat=True
            )
        )

        created, replaced, skipped = 0, 0, []
        with transaction.atomic():
            for row in rows:
                venue = venues.get(row.get("sheet_id"))
                if venue is None:
                    skipped.append(row.get("sheet_id") or "(no sheet_id)")
                    continue
                if venue.pk in already_saved:
                    replaced += 1
                else:
                    created += 1
                if not options["dry_run"]:
                    save_event_source(venue, row, checked_at=checked_at)

        prefix = "would have " if options["dry_run"] else ""
        self.stdout.write(f"{prefix}created {created}, {prefix}replaced {replaced}")
        if skipped:
            self.stdout.write(
                f"skipped {len(skipped)} rows for unknown venues: {', '.join(skipped)}"
            )
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("dry run: nothing saved"))
