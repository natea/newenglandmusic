import datetime
import json
import os
from io import StringIO
from pathlib import Path
from unittest import mock

from core.event_actions import actions_html
from core.management.commands import lookup_venue_places as lookup
from core.models import Event, Venue
from core.places import PlaceNotFound, PlacesError, to_place_dict
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

        def search(client, text, lat=None, lng=None):
            self.searches.append((text, lat, lng))
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
                ("Merriweather Post Pavilion, Washington, DC", 38.904722, -77.016389),
                ("Paradise Rock Club, Allston, MA", 42.3529, -71.1321),
            ],
        )

    def test_confident_match_is_saved_and_used(self):
        output = self.run_lookup(results=self.recorded_results)
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual(venue.place_lookup_status, Venue.PlaceLookupStatus.CONFIDENT)
        self.assertEqual(venue.place_id, "ChIJ4U6oQOh544kROegfjmsLBCs")
        self.assertIsNotNone(venue.place_looked_up_at)
        # the terms allow storing the place id and coordinates, and nothing else
        place_fields = {f.name for f in Venue._meta.get_fields() if f.name.startswith("place_")}
        self.assertEqual(
            place_fields,
            {
                "place_lookup_status", "place_looked_up_at", "place_id", "place_latitude", "place_longitude",
                # our own judgments of a review match, not places content
                "place_review_reasons", "place_distance_km",
            },
        )
        self.assertEqual((venue.place_review_reasons, venue.place_distance_km), ([], None))
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
        # the address is only reported, never stored
        self.assertIn("Columbia, MD", output)
        # not used: the sheet's coordinates stand
        self.assertEqual(venue.exact_location, (38.904722, -77.016389))
        self.assertIn("needs review: confirm or clear in the venue admin (1)", output)

    def test_different_name_needs_review(self):
        self.run_lookup(results={"Paradise Rock Club": [place("Agganis Arena")]})
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual(venue.place_lookup_status, Venue.PlaceLookupStatus.REVIEW)
        self.assertEqual(venue.place_id, "id-Agganis Arena")

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
        self.assertFalse(hasattr(venue, "place_business_status"))
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

    def test_contact_details_are_never_requested(self):
        # there's no option to ask for website or phone any more
        with self.assertRaises(CommandError):
            call_command("lookup_venue_places", "--contact", stdout=StringIO())

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
            stored = Event.all_objects.select_related("venue").get(pk=pk)
            # the pin is in the stored html; the map link in the icon row, made at page time
            self.assertIn('data-venue-lnglat="-71.1195,42.3519"', stored.baked_html_template)
            self.assertIn("query_place_id=id-Paradise Rock Club", actions_html(stored, set(), "/"))

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


def days_ago(days):
    return timezone.now() - datetime.timedelta(days=days)


class RefreshAndExpiryTestCase(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(
            sheet_id="V0089",
            name="Paradise Rock Club",
            city_town="Allston",
            state="MA",
            latitude=42.3529,
            longitude=-71.1321,
            place_lookup_status=Venue.PlaceLookupStatus.CONFIDENT,
            place_id="ChIJparadise",
            place_latitude=42.3519,
            place_longitude=-71.1195,
            place_looked_up_at=days_ago(26),
        )
        env = mock.patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "SECRETKEY"})
        env.start()
        self.addCleanup(env.stop)
        self.details_calls = []
        self.searches = []

    def lookup(self, *args, details=None):
        def place_details(client, place_id):
            self.details_calls.append(place_id)
            if isinstance(details, Exception):
                raise details
            return details or {
                "id": place_id, "latitude": 42.3518, "longitude": -71.1194,
                "business_status": "OPERATIONAL",
            }

        def search(client, text, lat=None, lng=None):
            self.searches.append(text)
            return []

        out = StringIO()
        with mock.patch.object(lookup.PlacesClient, "place_details", place_details), mock.patch.object(
            lookup.PlacesClient, "search_place", search
        ):
            call_command("lookup_venue_places", *args, stdout=out)
        return out.getvalue()

    def refreshed(self):
        return Venue.objects.get(pk=self.venue.pk)

    # refreshing by place id

    def test_stale_coordinates(self):
        self.lookup("--refresh-stale")
        self.assertEqual(self.details_calls, ["ChIJparadise"])
        venue = self.refreshed()
        self.assertEqual((venue.place_latitude, venue.place_longitude), (42.3518, -71.1194))
        self.assertGreater(venue.place_looked_up_at, days_ago(1))

    def test_fresh_coordinates(self):
        Venue.objects.filter(pk=self.venue.pk).update(place_looked_up_at=days_ago(3))
        self.lookup("--refresh-stale")
        self.assertEqual(self.details_calls, [])

    def test_max_age_days(self):
        Venue.objects.filter(pk=self.venue.pk).update(place_looked_up_at=days_ago(10))
        self.lookup("--refresh-stale", "--max-age-days", "7")
        self.assertEqual(self.details_calls, ["ChIJparadise"])

    def test_confirmed_match_survives_a_refresh(self):
        self.lookup("--refresh-stale")
        self.assertEqual(self.refreshed().place_lookup_status, Venue.PlaceLookupStatus.CONFIDENT)
        self.assertEqual(self.searches, [])

    def test_place_id_changed(self):
        self.lookup("--refresh-stale", details={
            "id": "ChIJmoved", "latitude": 42.3518, "longitude": -71.1194, "business_status": "OPERATIONAL",
        })
        self.assertEqual(self.refreshed().place_id, "ChIJmoved")

    def test_closed_venue_found_while_refreshing(self):
        output = self.lookup("--refresh-stale", details={
            "id": "ChIJparadise", "latitude": 42.3518, "longitude": -71.1194,
            "business_status": "CLOSED_PERMANENTLY",
        })
        self.assertIn("permanently closed: mark inactive in the sheet (1)", output)
        self.assertIn("V0089 Paradise Rock Club", output)
        self.assertIsNone(self.refreshed().is_active)

    # expiry

    def test_refresh_fails_past_the_limit(self):
        Venue.objects.filter(pk=self.venue.pk).update(place_looked_up_at=days_ago(31))
        output = self.lookup("--refresh-stale", details=PlacesError("place details: HTTP 503"))
        venue = self.refreshed()
        self.assertIsNone(venue.place_latitude)
        self.assertEqual((venue.place_id, venue.place_lookup_status), ("ChIJparadise", "confident"))
        self.assertEqual(venue.exact_location, (42.3529, -71.1321))
        self.assertIn("coordinates over 30 days old: deleted, using sheet coordinates (1)", output)

    def test_refresh_fails_within_the_limit(self):
        output = self.lookup("--refresh-stale", details=PlacesError("place details: HTTP 503"))
        self.assertEqual(self.refreshed().place_latitude, 42.3519)
        self.assertIn("V0089 Paradise Rock Club (Allston, MA): place details: HTTP 503", output)

    def test_missing_api_key_still_expires(self):
        Venue.objects.filter(pk=self.venue.pk).update(place_looked_up_at=days_ago(31))
        with mock.patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": ""}):
            with self.assertRaisesMessage(CommandError, "GOOGLE_PLACES_API_KEY is not set"):
                call_command("lookup_venue_places", stdout=StringIO())
        self.assertIsNone(self.refreshed().place_latitude)

    def test_expiry_runs_after_a_plain_lookup_too(self):
        Venue.objects.filter(pk=self.venue.pk).update(place_looked_up_at=days_ago(31))
        self.lookup()
        self.assertIsNone(self.refreshed().place_latitude)

    def test_expired_coordinates_restored(self):
        Venue.objects.filter(pk=self.venue.pk).update(
            place_looked_up_at=days_ago(31), place_latitude=None, place_longitude=None
        )
        self.lookup("--refresh-stale")
        venue = self.refreshed()
        self.assertEqual(venue.exact_location, (42.3518, -71.1194))

    # a place google no longer knows

    def test_place_gone(self):
        output = self.lookup("--refresh-stale", details=PlaceNotFound("place details: HTTP 404"))
        venue = self.refreshed()
        self.assertEqual((venue.place_id, venue.place_lookup_status), ("", ""))
        self.assertIsNone(venue.place_latitude)
        self.assertIn("no longer on google", output)
        self.lookup()
        self.assertEqual(self.searches, ["Paradise Rock Club, Allston, MA"])

    # stored event html

    def test_coordinates_expire_from_stored_html(self):
        event = Event.objects.create(title="show", starttime=timezone.now(), venue=self.venue)
        self.assertIn("42.3519", Event.all_objects.get(pk=event.pk).baked_html_template)
        Venue.objects.filter(pk=self.venue.pk).update(place_looked_up_at=days_ago(31))
        self.lookup("--refresh-stale", details=PlacesError("place details: HTTP 503"))
        html = Event.all_objects.get(pk=event.pk).baked_html_template
        self.assertNotIn("42.3519", html)
        self.assertIn('data-venue-lnglat="-71.1321,42.3529"', html)

    def test_refresh_returning_the_same_place_rebakes_nothing(self):
        with mock.patch.object(lookup, "rebake_events") as rebake:
            self.lookup("--refresh-stale", details={
                "id": "ChIJparadise", "latitude": 42.3519, "longitude": -71.1195,
                "business_status": "OPERATIONAL",
            })
        rebake.assert_not_called()

    # dry run

    def test_dry_run_saves_nothing(self):
        Venue.objects.create(
            sheet_id="V0090", name="Old", place_id="ChIJold", place_latitude=1.0,
            place_longitude=1.0, place_looked_up_at=days_ago(40),
        )
        output = self.lookup("--refresh-stale", "--dry-run")
        self.assertEqual(self.refreshed().place_latitude, 42.3519)
        self.assertEqual(Venue.objects.get(sheet_id="V0090").place_latitude, 1.0)
        self.assertIn("refreshed [dry run, not saved] (2)", output)
        self.assertIn("coordinates over 30 days old: would be deleted [dry run] (1)", output)


class ReviewReasonsTestCase(LookupVenuePlacesTestCase):
    def test_reasons_recorded(self):
        # "$3 Dewey's" style: another name, the right state, 0.4 km away
        self.run_lookup(results={"Paradise Rock Club": [place("Agganis Arena", lat=42.3529, lng=-71.1272)]})
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual(venue.place_lookup_status, Venue.PlaceLookupStatus.REVIEW)
        self.assertEqual((venue.place_review_reasons, venue.place_distance_km), (["name"], 0.4))

    def test_several_reasons(self):
        output = self.run_lookup(results={"Paradise Rock Club": [place("Agganis Arena", state="NH", lat=42.6, lng=-71.5)]})
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual(venue.place_review_reasons, ["name", "state", "distance"])
        self.assertGreater(venue.place_distance_km, 25)
        self.assertIn("[failed: name, state, distance]", output)

    def test_wrong_place_states_its_reason(self):
        self.run_lookup(results=self.recorded_results)
        # columbia, md is in another state, and over 25 km from the sheet's washington
        self.assertEqual(Venue.objects.get(pk=self.merriweather.pk).place_review_reasons, ["state", "distance"])

    def test_confident_match_has_no_reasons(self):
        Venue.objects.filter(pk=self.paradise.pk).update(place_review_reasons=["name"], place_distance_km=3.0)
        self.run_lookup("--refresh", results=self.recorded_results)
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual((venue.place_review_reasons, venue.place_distance_km), ([], None))

    def test_distance_expires_with_the_coordinates(self):
        Venue.objects.filter(pk=self.paradise.pk).update(
            place_lookup_status=Venue.PlaceLookupStatus.REVIEW, place_id="id-x", place_latitude=42.35,
            place_longitude=-71.12, place_looked_up_at=timezone.now() - datetime.timedelta(days=31),
            place_review_reasons=["name"], place_distance_km=0.4,
        )
        self.run_lookup()
        venue = Venue.objects.get(pk=self.paradise.pk)
        self.assertEqual((venue.place_latitude, venue.place_distance_km), (None, None))
        self.assertEqual(venue.place_review_reasons, ["name"])

    def test_backfilling_the_reasons(self):
        Venue.objects.filter(pk=self.paradise.pk).update(
            place_lookup_status=Venue.PlaceLookupStatus.REVIEW, place_looked_up_at=timezone.now()
        )
        Venue.objects.filter(pk=self.merriweather.pk).update(
            place_lookup_status=Venue.PlaceLookupStatus.CONFIDENT, place_looked_up_at=timezone.now()
        )
        self.run_lookup("--review", results={"Paradise Rock Club": [place("Agganis Arena")]})
        self.assertEqual([text for text, _, _ in self.searches], ["Paradise Rock Club, Allston, MA"])
        self.assertEqual(Venue.objects.get(pk=self.paradise.pk).place_review_reasons, ["name"])

    def test_review_dry_run(self):
        Venue.objects.filter(pk=self.paradise.pk).update(
            place_lookup_status=Venue.PlaceLookupStatus.REVIEW, place_looked_up_at=timezone.now()
        )
        output = self.run_lookup("--review", "--dry-run", results={"Paradise Rock Club": [place("Agganis Arena")]})
        self.assertIn("[failed: name]", output)
        self.assertEqual(Venue.objects.get(pk=self.paradise.pk).place_review_reasons, [])
