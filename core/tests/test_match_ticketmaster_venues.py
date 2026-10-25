import csv
import json
import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from core.event_fetching.ticketmaster import TicketmasterError, to_venue_dict
from core.management.commands import match_ticketmaster_venues as match
from core.models import Venue
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

FIXTURES = Path(__file__).parent / "fixtures" / "ticketmaster"
PARADISE = (42.35183, -71.11954)


def candidate(id, name, lat=None, lon=None, city="Boston"):
    return {
        "id": id,
        "name": name,
        "address": "1 Main St",
        "city": city,
        "state": "MA",
        "latitude": lat,
        "longitude": lon,
    }


class FindMatchTestCase(SimpleTestCase):
    def setUp(self):
        self.venue = Venue(name="Paradise Rock Club", latitude=PARADISE[0], longitude=PARADISE[1])

    def test_one_clear_match(self):
        outcome, found, _ = match.find_match(
            self.venue, [candidate("KovZpZA11JtA", "Paradise Rock Club", 42.3519, -71.1195)]
        )
        self.assertEqual((outcome, found["id"]), ("linked", "KovZpZA11JtA"))

    def test_recorded_search_with_duplicate_listing(self):
        data = json.loads((FIXTURES / "paradise_venues.json").read_text())
        candidates = [to_venue_dict(v) for v in data["_embedded"]["venues"]]
        outcome, found, scored = match.find_match(self.venue, candidates)
        # the second listing has no coordinates, so only the first is a confident match
        self.assertEqual((outcome, found["id"]), ("linked", "KovZpZA11JtA"))
        self.assertIsNone(scored[1]["distance_km"])

    def test_same_name_preferred_over_a_longer_one(self):
        venue = Venue(name="Big Night Live", latitude=42.3662, longitude=-71.0621)
        outcome, found, _ = match.find_match(
            venue,
            [
                candidate("play", "PLAY Boston at Big Night Live", 42.3663, -71.0622),
                candidate("bnl", "Big Night Live", 42.3662, -71.0621),
            ],
        )
        self.assertEqual((outcome, found["id"]), ("linked", "bnl"))

    def test_same_name_after_dropping_filler_words(self):
        # "Mr. Smalls Theatre" is mr smalls; the funhouse is a room inside it
        venue = Venue(name="Mr. Smalls", latitude=40.4801, longitude=-79.9624)
        outcome, found, _ = match.find_match(
            venue,
            [
                candidate("funhouse", "The Funhouse at Mr. Smalls", 40.4801, -79.9624),
                candidate("theatre", "Mr. Smalls Theatre", 40.4801, -79.9624),
            ],
        )
        self.assertEqual((outcome, found["id"]), ("linked", "theatre"))

    def test_several_merely_containing_the_name_are_ambiguous(self):
        venue = Venue(name="House of Blues", latitude=42.3471, longitude=-71.0949)
        outcome, _, _ = match.find_match(
            venue,
            [
                candidate("a", "Citizens House of Blues Boston", 42.3471, -71.0949),
                candidate("b", "Foundation Room at House of Blues Boston", 42.3471, -71.0949),
            ],
        )
        self.assertEqual(outcome, "ambiguous")

    def test_two_matches_nearby_are_ambiguous(self):
        outcome, found, scored = match.find_match(
            self.venue,
            [
                candidate("a", "Paradise Rock Club", 42.3519, -71.1195),
                candidate("b", "The Paradise Rock Club", 42.3520, -71.1196),
            ],
        )
        self.assertEqual((outcome, found), ("ambiguous", None))
        self.assertEqual(len(scored), 2)

    def test_distant_name_match_is_ambiguous(self):
        outcome, _, scored = match.find_match(
            self.venue, [candidate("a", "Paradise Rock Club", 42.3601, -71.0589)]
        )
        self.assertEqual(outcome, "ambiguous")
        self.assertGreater(scored[0]["distance_km"], match.MAX_DISTANCE_KM)

    def test_nearby_venue_with_another_name_is_not_a_match(self):
        outcome, _, _ = match.find_match(
            self.venue, [candidate("a", "Agganis Arena", 42.3519, -71.1195)]
        )
        self.assertEqual(outcome, "ambiguous")

    def test_confident_place_location_is_used(self):
        # the sheet has the town centre, 3 km off; google places has the venue
        venue = Venue(
            name="House of Blues",
            latitude=42.3605,
            longitude=-71.0596,
            place_lookup_status=Venue.PlaceLookupStatus.CONFIDENT,
            place_latitude=42.3471,
            place_longitude=-71.0949,
        )
        outcome, found, _ = match.find_match(
            venue, [candidate("hob", "House of Blues", 42.3470, -71.0950)]
        )
        self.assertEqual((outcome, found["id"]), ("linked", "hob"))

    def test_place_needing_review_is_not_used(self):
        venue = Venue(
            name="House of Blues",
            latitude=42.3605,
            longitude=-71.0596,
            place_lookup_status=Venue.PlaceLookupStatus.REVIEW,
            place_latitude=42.3471,
            place_longitude=-71.0949,
        )
        outcome, _, _ = match.find_match(
            venue, [candidate("hob", "House of Blues", 42.3470, -71.0950)]
        )
        self.assertEqual(outcome, "ambiguous")

    def test_venue_without_coordinates_is_ambiguous(self):
        outcome, _, _ = match.find_match(
            Venue(name="Paradise Rock Club"),
            [candidate("a", "Paradise Rock Club", 42.3519, -71.1195)],
        )
        self.assertEqual(outcome, "ambiguous")

    def test_no_candidates(self):
        self.assertEqual(match.find_match(self.venue, [])[0], "unmatched")


class MatchCommandTestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.report = os.path.join(self.tmp.name, "event_sources.csv")
        with open(self.report, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["sheet_id", "platforms"])
            writer.writeheader()
            writer.writerows(
                [
                    {"sheet_id": "V0089", "platforms": "ticketmaster"},
                    {"sheet_id": "V0074", "platforms": "eventbrite;ticketmaster"},
                    {"sheet_id": "V0200", "platforms": "eventbrite"},
                    {"sheet_id": "V0300", "platforms": "ticketmaster"},
                ]
            )
        self.paradise = Venue.objects.create(
            sheet_id="V0089",
            name="Paradise Rock Club",
            city_town="Allston",
            state="MA",
            latitude=PARADISE[0],
            longitude=PARADISE[1],
        )
        self.lincoln = Venue.objects.create(
            sheet_id="V0074", name="Lincoln Theatre", city_town="Washington", state="DC",
            ticketmaster_venue_id="manual-id",
        )
        Venue.objects.create(sheet_id="V0200", name="Eventbrite Only", state="MA")
        Venue.objects.create(sheet_id="V0300", name="Closed TM Venue", state="MA", is_active=False)
        Venue.objects.create(sheet_id="V0400", name="Not In Report", state="MA")
        env = mock.patch.dict(os.environ, {"TICKETMASTER_API_KEY": "test-key"})
        env.start()
        self.addCleanup(env.stop)
        self.searches = []

    def run_match(self, *args, results=None):
        results = results or {}

        def search(client, keyword, state):
            self.searches.append((keyword, state))
            result = results.get(keyword, [])
            if isinstance(result, Exception):
                raise result
            return result

        out = StringIO()
        with mock.patch.object(match.TicketmasterClient, "search_venues", search):
            call_command("match_ticketmaster_venues", "--report", self.report, *args, stdout=out)
        return out.getvalue()

    paradise_results = {
        "Paradise Rock Club": [candidate("KovZpZA11JtA", "Paradise Rock Club", 42.3519, -71.1195)]
    }

    def test_missing_api_key(self):
        with mock.patch.dict(os.environ, {"TICKETMASTER_API_KEY": ""}):
            with self.assertRaisesMessage(CommandError, "TICKETMASTER_API_KEY is not set"):
                call_command("match_ticketmaster_venues", stdout=StringIO())
        self.assertIsNone(Venue.objects.get(pk=self.paradise.pk).ticketmaster_venue_id)

    def test_default_selection_is_active_ticketmaster_venues(self):
        output = self.run_match(results=self.paradise_results)
        # lincoln is already linked; the closed venue, eventbrite-only and unreported venues are skipped
        self.assertEqual(self.searches, [("Paradise Rock Club", "MA")])
        self.paradise.refresh_from_db()
        self.assertEqual(self.paradise.ticketmaster_venue_id, "KovZpZA11JtA")
        self.assertIn("linked (1)", output)
        self.assertIn("V0089 Paradise Rock Club (Allston, MA) -> KovZpZA11JtA", output)
        self.assertIn("already linked (1)", output)
        self.assertIn("V0074 Lincoln Theatre (Washington, DC) -> manual-id", output)

    def test_existing_link_is_kept(self):
        self.run_match(results={"Lincoln Theatre": [candidate("other", "Lincoln Theatre")]})
        self.assertEqual(Venue.objects.get(pk=self.lincoln.pk).ticketmaster_venue_id, "manual-id")

    def test_recheck_looks_at_linked_venues_again(self):
        self.run_match("--recheck", results=self.paradise_results)
        self.assertIn(("Lincoln Theatre", "DC"), self.searches)

    def test_dry_run_saves_nothing(self):
        output = self.run_match("--dry-run", results=self.paradise_results)
        self.assertIsNone(Venue.objects.get(pk=self.paradise.pk).ticketmaster_venue_id)
        self.assertIn("linked [dry run, not saved] (1)", output)

    def test_sheet_ids(self):
        self.run_match("--sheet-ids", "V0200,V0300")
        self.assertEqual(
            sorted(self.searches), [("Closed TM Venue", "MA"), ("Eventbrite Only", "MA")]
        )

    def test_all_checks_every_active_venue(self):
        self.run_match("--all")
        names = {keyword for keyword, _ in self.searches}
        # nothing is found by name, so paradise's city is searched too
        self.assertEqual(
            names, {"Paradise Rock Club", "Allston", "Eventbrite Only", "Not In Report"}
        )

    def test_city_search_when_the_name_finds_nothing(self):
        self.run_match(
            "--sheet-ids",
            "V0089",
            results={"Allston": [candidate("p", "Paradise Rock Club", 42.3519, -71.1195)]},
        )
        self.assertEqual(self.searches, [("Paradise Rock Club", "MA"), ("Allston", "MA")])
        self.assertEqual(Venue.objects.get(pk=self.paradise.pk).ticketmaster_venue_id, "p")

    def test_other_spelling_of_theater_is_searched_too(self):
        state = Venue.objects.create(
            sheet_id="V0404", name="The State Theater", city_town="Portland", state="ME",
            latitude=43.6567, longitude=-70.2622,
        )
        self.run_match(
            "--sheet-ids",
            "V0404",
            results={
                "The State Theater": [candidate("b", "Maine State Music Theatre", 43.91, -69.96)],
                "The State Theatre": [candidate("KovZpa3mee", "State Theatre", 43.6567, -70.2622)],
            },
        )
        self.assertEqual(self.searches, [("The State Theater", "ME"), ("The State Theatre", "ME")])
        self.assertEqual(Venue.objects.get(pk=state.pk).ticketmaster_venue_id, "KovZpa3mee")

    def test_ambiguous_venue_is_reported_with_candidates(self):
        output = self.run_match(
            results={
                "Paradise Rock Club": [
                    candidate("a", "Paradise Rock Club", 42.3519, -71.1195),
                    candidate("b", "Paradise Rock Club", 42.3520, -71.1196),
                    candidate("c", "Paradise Rock Club"),
                ]
            }
        )
        self.assertIsNone(Venue.objects.get(pk=self.paradise.pk).ticketmaster_venue_id)
        self.assertIn("ambiguous: set the id in the admin if one of these is right (1)", output)
        self.assertIn("a  Paradise Rock Club, 1 Main St, Boston [0.01 km]", output)
        self.assertIn("c  Paradise Rock Club, 1 Main St, Boston [no coordinates]", output)

    def test_unmatched_and_failed_venues_are_reported_once(self):
        output = self.run_match(
            "--sheet-ids",
            "V0089,V0200",
            results={"Eventbrite Only": TicketmasterError("venues.json: HTTP 503")},
        )
        self.assertIn("unmatched (1)", output)
        self.assertEqual(output.count("V0089 Paradise Rock Club"), 1)
        self.assertIn("V0200 Eventbrite Only (MA): venues.json: HTTP 503", output)

    def test_missing_report_in_default_mode(self):
        with self.assertRaisesMessage(CommandError, "run check_event_sources first"):
            call_command(
                "match_ticketmaster_venues", "--report", "/nonexistent.csv", stdout=StringIO()
            )
