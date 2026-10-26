import json
import os
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.event_fetching.eventbrite import EventbriteClient, EventbriteError
from core.event_sources import save_event_source
from core.management.commands import match_eventbrite_organizers as match
from core.models import JobRun, Venue
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

FIXTURES = Path(__file__).parent / "fixtures" / "eventbrite"
# the recorded organizer's events are at the main pub, in manchester ct
MAIN_PUB = (41.7830, -72.5233)


def event_link(event_id):
    return f'<a href="https://www.eventbrite.com/e/some-show-tickets-{event_id}">tickets</a>'


def elsewhere(id):
    return {"id": id, "venue": {"name": "Some Other Bar", "latitude": "42.0", "longitude": "-71.0"}}


class MatchEventbriteOrganizersTestCase(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(
            sheet_id="V0026", name="The Main Pub", city_town="Manchester", state="CT",
            latitude=MAIN_PUB[0], longitude=MAIN_PUB[1],
        )
        save_event_source(self.venue, {
            "best_source": "ticketing", "url": "https://mainpub.example/",
            "events_page": "https://mainpub.example/events/", "platforms": "eventbrite",
        })
        self.pages = {}
        self.organizers = {}
        self.organizer_events = json.loads((FIXTURES / "organizer_events.json").read_text())["events"]
        self.lookups = []

        def event(client, event_id):
            self.lookups.append(event_id)
            return {"id": event_id, "organizer_id": self.organizers[event_id]}

        def organizer_events(client, organizer_id):
            if isinstance(self.organizer_events, Exception):
                raise self.organizer_events
            return self.organizer_events

        patches = [
            mock.patch.dict(os.environ, {"EVENTBRITE_API_KEY": "test"}),
            mock.patch.object(match, "robots_allows", return_value=True),
            mock.patch("requests.Session.get", side_effect=lambda url, timeout=None: SimpleNamespace(
                ok=url in self.pages, text=self.pages.get(url, ""))),
            mock.patch.object(EventbriteClient, "event", event),
            mock.patch.object(EventbriteClient, "organizer_events", organizer_events),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def match(self, *args):
        out = StringIO()
        call_command("match_eventbrite_organizers", *args, stdout=out, no_color=True)
        return out.getvalue()

    def linked_to(self):
        return Venue.objects.get(pk=self.venue.pk).eventbrite_organizer_id

    def link_events(self, organizers):
        """the events page links these events ({event id: organizer id})"""
        self.organizers = organizers
        self.pages["https://mainpub.example/events/"] = "".join(map(event_link, self.organizers))

    def test_one_organizer(self):
        self.link_events({"707179501927": "20010471604", "707179501928": "20010471604", "707179501929": "20010471604"})
        output = self.match()
        self.assertEqual(self.linked_to(), "20010471604")
        self.assertIn("linked (1)", output)
        self.assertIn("V0026 The Main Pub (Manchester, CT) -> organizer 20010471604: 3 live events, 3 at this venue", output)
        self.assertEqual(dict(JobRun.objects.get().summary)["linked"], 1)

    def test_several_organizers(self):
        self.link_events({"707179501927": "20010471604", "707179501928": "99999999999"})
        output = self.match()
        self.assertIsNone(self.linked_to())
        self.assertIn("several organizers: set the id in the admin if one of these is right (1)", output)
        self.assertIn("V0026 The Main Pub (Manchester, CT): 20010471604, 99999999999", output)

    def test_organizer_page_linked(self):
        self.pages["https://mainpub.example/"] = (
            '<a href="https://www.eventbrite.com/o/the-main-pub-20010471604">us on eventbrite</a>'
            + event_link("707179501927")
        )
        self.match()
        self.assertEqual(self.linked_to(), "20010471604")
        # the organizer link is enough, so no event is looked up
        self.assertEqual(self.lookups, [])

    def test_organizers_events_are_all_elsewhere(self):
        self.link_events({"707179501927": "53123971823"})
        self.organizer_events = [elsewhere("1"), elsewhere("2")]
        output = self.match()
        self.assertIsNone(self.linked_to())
        self.assertIn("events elsewhere: the organizer's live events are all at other venues (1)", output)
        self.assertIn("organizer 53123971823: 2 live events, 0 at this venue", output)

    def test_organizer_with_no_live_events_is_linked(self):
        self.link_events({"707179501927": "97629837253"})
        self.organizer_events = []
        self.match()
        self.assertEqual(self.linked_to(), "97629837253")

    def test_no_links(self):
        self.pages["https://mainpub.example/events/"] = "<p>call the bar for tickets</p>"
        output = self.match()
        self.assertIsNone(self.linked_to())
        self.assertIn("no eventbrite links on the venue's pages (1)", output)

    def test_dry_run_saves_nothing(self):
        self.link_events({"707179501927": "20010471604"})
        output = self.match("--dry-run")
        self.assertIsNone(self.linked_to())
        self.assertIn("linked [dry run, not saved] (1)", output)

    def test_already_linked_venues_are_skipped_unless_rechecked(self):
        Venue.objects.filter(pk=self.venue.pk).update(eventbrite_organizer_id="11111111111")
        self.link_events({"707179501927": "20010471604"})
        output = self.match()
        self.assertIn("V0026 The Main Pub (Manchester, CT) -> 11111111111", output)
        self.assertEqual(self.lookups, [])
        self.match("--recheck")
        self.assertEqual(self.linked_to(), "20010471604")

    def test_failure_is_reported_and_other_venues_continue(self):
        other = Venue.objects.create(sheet_id="V0198", name="The Haven", state="MA")
        save_event_source(other, {
            "best_source": "ticketing", "url": "https://haven.example/", "platforms": "eventbrite",
        })
        self.pages["https://haven.example/"] = '<a href="https://www.eventbrite.com/o/haven-14327783302">x</a>'
        self.link_events({"707179501927": "20010471604"})
        calls = []

        def organizer_events(client, organizer_id):
            calls.append(organizer_id)
            if organizer_id == "20010471604":
                raise EventbriteError("organizers/20010471604/events/: HTTP 500")
            return []

        with mock.patch.object(EventbriteClient, "organizer_events", organizer_events):
            output = self.match()
        self.assertIn("V0026 The Main Pub (Manchester, CT): organizers/20010471604/events/: HTTP 500", output)
        self.assertEqual(Venue.objects.get(pk=other.pk).eventbrite_organizer_id, "14327783302")

    def test_default_checks_only_venues_linking_eventbrite(self):
        Venue.objects.create(sheet_id="V0099", name="Unrelated", state="CT")
        self.link_events({"707179501927": "20010471604"})
        output = self.match()
        self.assertNotIn("Unrelated", output)
        self.assertIn("Unrelated", self.match("--all"))

    def test_needs_the_key(self):
        with mock.patch.dict(os.environ, {"EVENTBRITE_API_KEY": ""}):
            with self.assertRaisesMessage(CommandError, "EVENTBRITE_API_KEY is not set"):
                self.match()
