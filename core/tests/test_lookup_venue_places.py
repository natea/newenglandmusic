import json
import os
from io import StringIO
from pathlib import Path
from unittest import mock

from core.management.commands import lookup_venue_places as lookup
from core.models import Event, Venue
from core.places import PlacesError, to_place_dict
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

FIXTURES = Path(__file__).parent / "fixtures" / "places"


def recorded(name):
    data = json.loads((FIXTURES / f"{name}.json").read_text())
    return [to_place_dict(place) for place in data["places"]]


def place(name, state="MA", lat=42.3519, lng=-71.1195, **fields):
    return {
        "id": f"id-{name}",
        "name": name,
        "address": f"1 Main St, Boston, {state}",
        "state": state,
        "latitude": lat,
        "longitude": lng,
        "business_status": "OPERATIONAL",
        "maps_url": f"https://maps.google.com/?cid={name}",
        "website": "",
        "phone": "",
        **fields,
    }


class LookupVenuePlacesTestCase(TestCase):
    def setUp(self):
        self.paradise = Venue.objects.create(
            sheet_id="V0089",
            name="Paradise Rock Club",
            city_town="Allston",
            state="MA",
            latitude=42.3529,
            longitude=-71.1321,
            is_active=True,
            age_policy="18+",
        )
        self.merriweather = Venue.objects.create(
            sheet_id="V0075",
            name="Merriweather Post Pavilion",
            city_town="Washington",
            state="DC",
            latitude=38.904722,
            longitude=-77.016389,
        )
        self.closed = Venue.objects.create(sheet_id="V0900", name="Closed One", is_active=False)
        env = mock.patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "SECRETKEY"})
        env.start()
        self.addCleanup(env.stop)
        self.searches = []

    def run_lookup(self, *args, results=None):
        results = results or {}

        def search(client, text, lat=None, lng=None, contact=False):
            self.searches.append((text, lat, lng, contact))
            result = results.get(text.split(",")[0], [])
            if isinstance(result, Exception):
                raise result
            return result

        out = StringIO()
        with mock.patch.object(lookup.PlacesClient, "search_place", search):
            call_command("lookup_venue_places", *args, stdout=out)
        return out.getvalue()

    recorded_results = {
        "Paradise Rock Club": recorded("paradise"),
        "Merriweather Post Pavilion": recorded("merriweather"),
    }

    def test_missing_api_key(self):
        with mock.patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": ""}):
            with self.assertRaisesMessage(CommandError, "GOOGLE_PLACES_API_KEY is not set"):
                call_command("lookup_venue_places", stdout=StringIO())
        self.assertEqual(Venue.objects.get(pk=self.paradise.pk).place_lookup_status, "")

    def test_searches_active_venues_by_name_town_and_state(self):
        self.run_lookup(results=self.recorded_results)
        self.assertEqual(
            self.searches,
            [
                ("Merriweather Post Pavilion, Washington, DC", 38.904722, -77.016389, False),
                ("Paradise Rock Club, Allston, MA", 42.3529, -71.1321, False),
            ],
        )

    def test_confident_match_is_saved_and_used(self):
        output = self.run_lookup(results=self.recorded_results)
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual(venue.place_lookup_status, Venue.PlaceLookupStatus.CONFIDENT)
        self.assertEqual(venue.place_id, "ChIJ4U6oQOh544kROegfjmsLBCs")
        self.assertEqual(venue.place_address, "967 Commonwealth Ave, Boston, MA 02215, USA")
        self.assertEqual(venue.place_business_status, "OPERATIONAL")
        self.assertIsNotNone(venue.place_looked_up_at)
        self.assertAlmostEqual(venue.exact_location[0], 42.3518, places=3)
        # fields from the sheet are untouched
        self.assertEqual((venue.latitude, venue.age_policy, venue.is_active), (42.3529, "18+", True))
        self.assertIn("confident (1)", output)
        self.assertIn("V0089 Paradise Rock Club (Allston, MA) -> Paradise Rock Club, 967 Commonwealth Ave", output)

    def test_wrong_state_needs_review(self):
        # the sheet says washington, dc; google finds it in columbia, md
        output = self.run_lookup(results=self.recorded_results)
        venue = Venue.objects.get(pk=self.merriweather.pk)
        self.assertEqual(venue.place_lookup_status, Venue.PlaceLookupStatus.REVIEW)
        self.assertIn("Columbia, MD", venue.place_address)
        # not used: the sheet's coordinates stand
        self.assertEqual(venue.exact_location, (38.904722, -77.016389))
        self.assertIn("needs review: confirm or clear in the venue admin (1)", output)

    def test_different_name_needs_review(self):
        self.run_lookup(results={"Paradise Rock Club": [place("Agganis Arena")]})
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual(venue.place_lookup_status, Venue.PlaceLookupStatus.REVIEW)
        self.assertEqual(venue.place_name, "Agganis Arena")

    def test_too_far_away_needs_review(self):
        self.run_lookup(results={"Paradise Rock Club": [place("Paradise Rock Club", lat=41.0, lng=-72.0)]})
        self.assertEqual(
            Venue.objects.get(pk=self.paradise.pk).place_lookup_status,
            Venue.PlaceLookupStatus.REVIEW,
        )

    def test_first_matching_result_of_the_top_few_wins(self):
        self.run_lookup(
            results={
                "Paradise Rock Club": [
                    place("Agganis Arena"),
                    place("Paradise Rock Club", state="NH"),
                    place("Paradise Rock Club", id="the-right-one"),
                ]
            }
        )
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual(venue.place_lookup_status, Venue.PlaceLookupStatus.CONFIDENT)
        self.assertEqual(venue.place_id, "the-right-one")

    def test_venue_without_coordinates_can_still_match(self):
        Venue.objects.filter(pk=self.paradise.pk).update(latitude=None, longitude=None)
        self.run_lookup(results={"Paradise Rock Club": [place("Paradise Rock Club")]})
        self.assertEqual(
            Venue.objects.get(pk=self.paradise.pk).place_lookup_status,
            Venue.PlaceLookupStatus.CONFIDENT,
        )

    def test_nothing_found(self):
        output = self.run_lookup()
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual(venue.place_lookup_status, Venue.PlaceLookupStatus.NOT_FOUND)
        self.assertEqual(venue.place_id, "")
        self.assertIn("not found (2)", output)

    def test_closed_venue_is_reported_not_deactivated(self):
        output = self.run_lookup(
            results={"Paradise Rock Club": [place("Paradise Rock Club", business_status="CLOSED_PERMANENTLY")]}
        )
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual(venue.place_business_status, "CLOSED_PERMANENTLY")
        self.assertIs(venue.is_active, True)
        self.assertIn("permanently closed: mark inactive in the sheet (1)", output)

    def test_looked_up_venues_are_skipped_unless_refreshed(self):
        self.run_lookup(results=self.recorded_results)
        self.searches.clear()
        self.run_lookup(results=self.recorded_results)
        self.assertEqual(self.searches, [])
        self.run_lookup("--refresh", results=self.recorded_results)
        self.assertEqual(len(self.searches), 2)

    def test_selection_options(self):
        self.run_lookup("--state", "dc")
        self.assertEqual([s[0] for s in self.searches], ["Merriweather Post Pavilion, Washington, DC"])
        self.searches.clear()
        self.run_lookup("--sheet-ids", "V0900", "--refresh")
        self.assertEqual([s[0] for s in self.searches], ["Closed One"])
        self.searches.clear()
        self.run_lookup("--limit", "1", "--refresh")
        self.assertEqual(len(self.searches), 1)

    def test_contact_details_only_when_asked(self):
        found = {"Paradise Rock Club": [place("Paradise Rock Club", website="https://p.example", phone="(617) 555-0100")]}
        self.run_lookup(results=found)
        self.assertEqual(Venue.objects.get(pk=self.paradise.pk).place_website, "")
        self.run_lookup("--refresh", "--contact", results=found)
        self.assertTrue(self.searches[-1][3])
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual((venue.place_website, venue.place_phone), ("https://p.example", "(617) 555-0100"))

    def test_dry_run_saves_nothing(self):
        output = self.run_lookup("--dry-run", results=self.recorded_results)
        self.assertEqual(Venue.objects.get(pk=self.paradise.pk).place_lookup_status, "")
        self.assertIn("confident [dry run, not saved] (1)", output)

    def test_changed_location_updates_events_map_pin(self):
        event = Event.objects.create(title="show", starttime=timezone.now(), venue=self.paradise)
        unapproved = Event.objects.create(
            title="pending", starttime=timezone.now(), venue=self.paradise, is_approved=False
        )
        self.assertIn('data-venue-lnglat="-71.1321,42.3529"', Event.all_objects.get(pk=event.pk).baked_html_template)
        self.run_lookup(results={"Paradise Rock Club": [place("Paradise Rock Club")]})
        for pk in (event.pk, unapproved.pk):
            html = Event.all_objects.get(pk=pk).baked_html_template
            self.assertIn('data-venue-lnglat="-71.1195,42.3519"', html)
            self.assertIn("cid=Paradise Rock Club", html)

    def test_failed_request_is_reported_and_others_continue(self):
        Venue.objects.filter(pk=self.paradise.pk).update(place_id="kept", place_lookup_status="")
        output = self.run_lookup(
            results={
                "Paradise Rock Club": PlacesError("places search: HTTP 503"),
                "Merriweather Post Pavilion": recorded("merriweather"),
            }
        )
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual((venue.place_id, venue.place_lookup_status), ("kept", ""))
        self.assertIn("V0089 Paradise Rock Club (Allston, MA): places search: HTTP 503", output)
        self.assertEqual(
            Venue.objects.get(pk=self.merriweather.pk).place_lookup_status,
            Venue.PlaceLookupStatus.REVIEW,
        )
        self.assertNotIn("SECRETKEY", output)
