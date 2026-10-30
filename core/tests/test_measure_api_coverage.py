import json
import os
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.event_fetching.eventbrite import EventbriteClient
from core.event_fetching.seatgeek import SeatGeekClient, SeatGeekError, to_venue_dict
from core.event_sources import save_event_source
from core.management.commands import match_eventbrite_organizers as match
from core.models import JobRun, Venue, VenueEventSource
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

FIXTURES = Path(__file__).parent / "fixtures" / "eventbrite"
SEATGEEK_FIXTURES = Path(__file__).parent / "fixtures" / "seatgeek"

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


class MeasureSeatGeekCoverageTestCase(TestCase):
    """the seatgeek half, with eventbrite off and the seatgeek client mocked"""

    def setUp(self):
        self.sinclair = Venue.objects.create(
            sheet_id="V0152", name="The Sinclair", city_town="Cambridge", state="MA",
            latitude=42.3740, longitude=-71.1206,
        )
        save_event_source(self.sinclair, {
            "best_source": "ticketing", "url": "https://sinclair.example/", "platforms": "axs",
        })
        self.toads = Venue.objects.create(
            sheet_id="V0042", name="Toad's Place", city_town="New Haven", state="CT",
            latitude=41.308, longitude=-72.9244, ticketmaster_venue_id="tm1",
        )
        save_event_source(self.toads, {
            "best_source": "ticketing", "url": "https://toads.example/", "platforms": "etix",
        })
        searches = {
            "MA": [to_venue_dict(v) for v in self.load("venues_sinclair.json")["venues"]],
            "CT": [to_venue_dict(v) for v in self.load("venues_toads.json")["venues"]],
        }
        patches = [
            mock.patch.dict(os.environ, {"EVENTBRITE_API_KEY": "", "SEATGEEK_CLIENT_ID": "test"}),
            mock.patch.object(SeatGeekClient, "search_venues", side_effect=lambda name, state: searches[state]),
            mock.patch.object(
                SeatGeekClient, "venue_events", return_value=self.load("events_sinclair.json")["events"]
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def load(self, name):
        return json.loads((SEATGEEK_FIXTURES / name).read_text())

    def measure(self, *args):
        out = StringIO()
        call_command("measure_api_coverage", *args, stdout=out, no_color=True)
        return out.getvalue()

    def test_reports_the_match_and_its_concerts(self):
        output = self.measure()
        # two of the five recorded events are concerts
        self.assertIn("seatgeek venue 11280 The Sinclair - Cambridge: 5 upcoming events, 2 concerts\n", output)
        self.assertIn(
            "seatgeek venue 1075 Toad's Place: 5 upcoming events, 2 concerts (already linked to ticketmaster)",
            output,
        )
        self.assertIn(
            "seatgeek: matched 2 of 2 venues; 2 have upcoming concerts there (4 concerts), "
            "1 of them not linked to ticketmaster or eventbrite",
            output,
        )
        # eventbrite is off, so it has no totals line
        self.assertNotIn("eventbrite: organizer found", output)

    def test_summary_is_recorded(self):
        self.measure()
        summary = dict(JobRun.objects.get().summary)
        self.assertEqual(summary["seatgeek matched"], 2)
        self.assertEqual(summary["seatgeek concerts"], 4)
        self.assertEqual(summary["seatgeek with concerts, not on ticketmaster or eventbrite"], 1)

    def test_no_certain_match_lists_the_candidates(self):
        Venue.objects.filter(pk=self.sinclair.pk).update(latitude=42.0, longitude=-71.5)
        output = self.measure("--sheet-ids", "V0152")
        self.assertIn("seatgeek: no certain match among", output)
        self.assertRegex(output, r"11280 The Sinclair - Cambridge, Cambridge \[\d+\.\d\d km\]")

    def test_api_error_is_reported_and_the_run_goes_on(self):
        with mock.patch.object(SeatGeekClient, "search_venues", side_effect=SeatGeekError("venues: HTTP 500")):
            output = self.measure()
        self.assertEqual(output.count("seatgeek failed: venues: HTTP 500"), 2)
