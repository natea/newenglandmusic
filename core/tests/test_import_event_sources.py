import csv
import datetime
import os
import tempfile
from io import StringIO
from unittest import mock

from core.event_sources import CSV_COLUMNS
from core.models import Venue, VenueEventSource
from django.core.management import call_command
from django.test import TestCase


def row(sheet_id, best_source="ical", **values):
    values = {"sheet_id": sheet_id, "best_source": best_source, **values}
    return {column: values.get(column, "") for column in CSV_COLUMNS}


class ImportEventSourcesTestCase(TestCase):
    def setUp(self):
        for sheet_id in ("V0001", "V0002", "V0003"):
            Venue.objects.create(
                sheet_id=sheet_id, name=f"Venue {sheet_id}", state="VT"
            )
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = os.path.join(tmp.name, "event_sources.csv")
        with open(self.path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(
                [
                    row(
                        "V0001",
                        ical_url="https://v0001.example/cal.ics",
                        ical_events="12",
                    ),
                    row("V0002", "ticketing", platforms="dice;ticketmaster"),
                    row("V0003", "ai-extraction", js_heavy="yes"),
                    row("V9999", "json-ld", json_ld_events="4"),
                ]
            )
        self.modified = datetime.datetime(
            2026, 10, 24, 12, 0, tzinfo=datetime.timezone.utc
        )
        os.utime(self.path, (self.modified.timestamp(), self.modified.timestamp()))
        # nothing is crawled: any request fails the test
        patcher = mock.patch(
            "requests.Session.request", side_effect=AssertionError("crawled")
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_import(self, *args):
        out = StringIO()
        call_command("import_event_sources", self.path, *args, stdout=out)
        return out.getvalue()

    def test_import_an_existing_report(self):
        output = self.run_import()
        self.assertEqual(VenueEventSource.objects.count(), 3)
        source = VenueEventSource.objects.get(venue__sheet_id="V0001")
        self.assertEqual(source.ical_events, 12)
        self.assertEqual(source.checked_at, self.modified)
        self.assertEqual(
            VenueEventSource.objects.get(venue__sheet_id="V0002").platforms,
            ["dice", "ticketmaster"],
        )
        self.assertIn("created 3, replaced 0", output)
        self.assertIn("skipped 1 rows for unknown venues: V9999", output)

    def test_import_replaces_saved_results(self):
        self.run_import()
        output = self.run_import()
        self.assertEqual(VenueEventSource.objects.count(), 3)
        self.assertIn("created 0, replaced 3", output)

    def test_import_dry_run(self):
        output = self.run_import("--dry-run")
        self.assertEqual(VenueEventSource.objects.count(), 0)
        self.assertIn("would have created 3", output)
        self.assertIn("nothing saved", output)
