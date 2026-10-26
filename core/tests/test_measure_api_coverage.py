import json
import os
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.event_fetching.eventbrite import EventbriteClient
from core.event_sources import save_event_source
from core.management.commands import match_eventbrite_organizers as match
from core.models import JobRun, Venue, VenueEventSource
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

FIXTURES = Path(__file__).parent / "fixtures" / "eventbrite"

PAGES = {
    # the main pub links its eventbrite events
    "https://mainpub.example/events/": (
        '<a href="https://www.eventbrite.com/e/7-below-tickets-707179501927">tix</a>'
    ),
    # etix venue: nothing eventbrite on its page
    "https://etix.example/": "<a href='https://www.etix.com/ticket/p/1'>tix</a>",
}


class MeasureCoverageTestCase(TestCase):
    def setUp(self):
        self.main_pub = Venue.objects.create(
            sheet_id="V0026", name="The Main Pub", city_town="Manchester", state="CT",
            latitude=41.7830, longitude=-72.5233,
        )
        self.etix = Venue.objects.create(sheet_id="V0024", name="The Webster", state="CT")
        Venue.objects.create(sheet_id="V0099", name="Unrelated", state="CT")
        save_event_source(self.main_pub, {
            "best_source": "ticketing", "url": "https://mainpub.example/",
            "events_page": "https://mainpub.example/events/", "platforms": "eventbrite",
        })
        save_event_source(self.etix, {
            "best_source": "ticketing", "url": "https://etix.example/", "platforms": "etix",
        })
        patches = [
            mock.patch.dict(os.environ, {"EVENTBRITE_API_KEY": "test", "SEATGEEK_CLIENT_ID": ""}),
            mock.patch.object(match, "robots_allows", return_value=True),
            mock.patch("requests.Session.get", side_effect=lambda url, timeout=None: SimpleNamespace(
                ok=url in PAGES, text=PAGES.get(url, ""))),
            mock.patch.object(EventbriteClient, "event", return_value={"organizer_id": "20010471604"}),
            mock.patch.object(
                EventbriteClient, "organizer_events",
                return_value=json.loads((FIXTURES / "organizer_events.json").read_text())["events"]
                + [{"id": "elsewhere", "venue": {"name": "Some Other Bar", "latitude": "42.0", "longitude": "-71.0"}}],
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def measure(self, *args):
        out = StringIO()
        call_command("measure_api_coverage", *args, stdout=out, no_color=True)
        return out.getvalue()

    def test_reports_organizer_and_events_at_the_venue(self):
        output = self.measure()
        self.assertIn("V0026 The Main Pub (Manchester, CT) [eventbrite]", output)
        self.assertIn("eventbrite organizer 20010471604: 4 live events, 3 at this venue", output)
        self.assertIn("V0024 The Webster", output)
        self.assertIn("eventbrite: no links found", output)
        self.assertNotIn("Unrelated", output)
        self.assertIn("seatgeek: skipped (no SEATGEEK_CLIENT_ID)", output)

    def test_saves_nothing_but_its_job_run(self):
        self.measure()
        self.assertEqual(Venue.objects.get(pk=self.main_pub.pk).ticketmaster_venue_id, None)
        self.assertEqual(VenueEventSource.objects.count(), 2)
        run = JobRun.objects.get()
        self.assertEqual(dict(run.summary)["with events here"], 1)

    def test_includes_problem_venues_from_the_latest_full_fetch(self):
        problem = Venue.objects.create(sheet_id="V0594", name="Montage Music Hall", state="NY")
        JobRun.objects.create(
            command="fetch_events", arguments={"all": True}, started_at=timezone.now(),
            problems=[{"venue_id": problem.pk, "sheet_id": "V0594", "name": problem.name, "problems": ["failed: x"]}],
        )
        self.assertIn("V0594 Montage Music Hall", self.measure())
