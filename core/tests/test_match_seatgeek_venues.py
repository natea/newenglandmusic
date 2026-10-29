import json
import os
from io import StringIO
from pathlib import Path
from unittest import mock

from core.event_fetching.seatgeek import SeatGeekClient, SeatGeekError, to_venue_dict
from core.event_sources import save_event_source
from core.models import JobRun, Venue
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

FIXTURES = Path(__file__).parent / "fixtures" / "seatgeek"


def recorded_venues(name):
    return [to_venue_dict(v) for v in json.loads((FIXTURES / name).read_text())["venues"]]


def candidate(id, name, lat, lon, events):
    return {
        "id": id, "name": name, "address": "1 Church St", "city": "Cambridge", "state": "MA",
        "latitude": lat, "longitude": lon, "upcoming_events": events,
    }


class MatchSeatGeekVenuesTestCase(TestCase):
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
            latitude=41.308, longitude=-72.9244,
        )
        save_event_source(self.toads, {
            "best_source": "ticketing", "url": "https://toads.example/", "platforms": "etix",
        })
        # no etix, axs or eventbrite links, so not checked by default
        self.other = Venue.objects.create(
            sheet_id="V0099", name="Elsewhere Bar", city_town="Boston", state="MA",
            latitude=42.35, longitude=-71.06,
        )
        self.searches = {
            "MA": recorded_venues("venues_sinclair.json"),
            "CT": recorded_venues("venues_toads.json"),
        }
        patches = [
            mock.patch.dict(os.environ, {"SEATGEEK_CLIENT_ID": "test"}),
            mock.patch.object(
                SeatGeekClient, "search_venues",
                side_effect=lambda name, state: self.searches[state],
            ),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def match(self, *args):
        out = StringIO()
        call_command("match_seatgeek_venues", *args, stdout=out, no_color=True)
        return out.getvalue()

    def linked_id(self, venue):
        return Venue.objects.get(pk=venue.pk).seatgeek_venue_id

    def test_one_clear_match(self):
        output = self.match()
        # "The Sinclair - Cambridge" is the only listing, at the venue's location
        self.assertEqual(self.linked_id(self.sinclair), "11280")
        # toad's place over the empty "Lilly's Pad (Toad's Place Upstairs)" next door
        self.assertEqual(self.linked_id(self.toads), "1075")
        self.assertIn("V0152 The Sinclair", output)
        self.assertIsNone(self.linked_id(self.other))

    def test_ambiguous(self):
        self.searches["MA"] = [
            candidate("1", "The Sinclair Upstairs", 42.3741, -71.1207, 4),
            candidate("2", "The Sinclair Downstairs", 42.3742, -71.1205, 9),
        ]
        output = self.match("--sheet-ids", "V0152")
        self.assertIsNone(self.linked_id(self.sinclair))
        self.assertIn("ambiguous: set the id in the admin if one of these is right (1)", output)
        self.assertIn("1  The Sinclair Upstairs, 1 Church St, Cambridge [0.01 km, 4 upcoming events]", output)
        self.assertIn("2  The Sinclair Downstairs", output)

    def test_missing_client_id(self):
        with mock.patch.dict(os.environ, {"SEATGEEK_CLIENT_ID": ""}):
            with self.assertRaisesMessage(CommandError, "SEATGEEK_CLIENT_ID is not set"):
                self.match()

    def test_dry_run_saves_nothing(self):
        output = self.match("--dry-run")
        self.assertIn("[dry run, not saved]", output)
        self.assertIsNone(self.linked_id(self.sinclair))

    def test_existing_link_is_kept_unless_rechecked(self):
        Venue.objects.filter(pk=self.sinclair.pk).update(seatgeek_venue_id="999")
        self.assertIn("V0152 The Sinclair (", self.match().split("already linked")[1])
        self.assertEqual(self.linked_id(self.sinclair), "999")
        self.match("--recheck")
        self.assertEqual(self.linked_id(self.sinclair), "11280")

    def test_all_checks_every_active_venue(self):
        self.searches["MA"] = self.searches["MA"] + [
            candidate("77", "Elsewhere Bar", 42.35, -71.06, 3),
        ]
        self.match("--all")
        self.assertEqual(self.linked_id(self.other), "77")

    def test_failed_search_is_reported_and_the_run_goes_on(self):
        def search(name, state):
            if state == "CT":
                raise SeatGeekError("venues: HTTP 500")
            return self.searches[state]

        with mock.patch.object(SeatGeekClient, "search_venues", side_effect=search):
            output = self.match()
        self.assertIn("V0042 Toad's Place (", output.split("failed")[1])
        self.assertIn("venues: HTTP 500", output)
        self.assertEqual(self.linked_id(self.sinclair), "11280")

    def test_run_is_recorded(self):
        self.match()
        run = JobRun.objects.get(command="match_seatgeek_venues")
        self.assertEqual(dict(run.summary)["linked"], 2)
