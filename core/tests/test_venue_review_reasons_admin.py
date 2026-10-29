import datetime
import os
from unittest import mock

from core.models import Event, Venue
from core.places import PlacesClient, PlacesError
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

Status = Venue.PlaceLookupStatus


def review(name, reasons, km, **fields):
    return Venue.objects.create(
        name=name, sheet_id=name[:5], place_lookup_status=Status.REVIEW, place_id=f"id-{name}",
        place_review_reasons=reasons, place_distance_km=km, **fields,
    )


class ReviewReasonsAdminTestCase(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.dewey = review("$3 Dewey's", ["name"], 0.4)
        self.merriweather = review("Merriweather Post Pavilion", ["state", "distance"], 38.2)
        self.unrecorded = review("Old Review", [], None)
        self.park = review("Spicket River Brewery", ["type"], 1.5)
        Venue.objects.create(name="Paradise Rock Club", place_lookup_status=Status.CONFIDENT)

    def changelist(self, query=""):
        return self.client.get(reverse("admin:core_venue_changelist") + query)

    def test_why_a_venue_needs_review(self):
        html = self.changelist("?place_lookup_status__exact=review").content.decode()
        self.assertIn("name differs · 0.4 km away", html)
        self.assertIn("in another state · 38.2 km away (over 25)", html)
        self.assertIn("not recorded (run lookup_venue_places --review)", html)
        self.assertIn("not a venue · 1.5 km away", html)

    def test_filter_by_reason(self):
        names = {v.name for v in self.changelist("?review_reason=state").context["cl"].result_list}
        self.assertEqual(names, {"Merriweather Post Pavilion"})
        names = {v.name for v in self.changelist("?review_reason=name").context["cl"].result_list}
        self.assertEqual(names, {"$3 Dewey's"})
        names = {v.name for v in self.changelist("?review_reason=type").context["cl"].result_list}
        self.assertEqual(names, {"Spicket River Brewery"})

    def test_actions_clear_the_reasons(self):
        url = reverse("admin:core_venue_changelist")
        self.client.post(url, {"action": "mark_place_as_confident", "_selected_action": [self.dewey.pk]})
        self.client.post(url, {"action": "clear_place_lookup", "_selected_action": [self.merriweather.pk]})
        for venue in (self.dewey, self.merriweather):
            venue.refresh_from_db()
            self.assertEqual((venue.place_review_reasons, venue.place_distance_km), ([], None))
        self.assertEqual(self.dewey.place_lookup_status, Status.CONFIDENT)


class GoogleNameAdminTestCase(TestCase):
    """google's name for a review venue's place: asked for live, shown, never saved"""

    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.dewey = review("$3 Dewey's", ["name"], 0.4)
        self.paradise = Venue.objects.create(
            name="Paradise Rock Club", place_lookup_status=Status.CONFIDENT, place_id="id-paradise"
        )
        env = mock.patch.dict(os.environ, {"GOOGLE_PLACES_API_KEY": "SECRETKEY"})
        env.start()
        self.addCleanup(env.stop)
        name = mock.patch.object(PlacesClient, "place_name", return_value="Three Dollar Deweys")
        self.place_name = name.start()
        self.addCleanup(name.stop)

    def name_url(self, venue):
        return reverse("admin:core_venue_google_name", args=[venue.pk])

    def test_the_list_asks_google_nothing(self):
        html = self.client.get(reverse("admin:core_venue_changelist")).content.decode()
        self.place_name.assert_not_called()
        # a link for the review venue only
        self.assertIn(f'href="{self.name_url(self.dewey)}" data-google-name', html)
        self.assertNotIn(self.name_url(self.paradise), html)
        self.assertIn("https://www.google.com/maps/place/?q=place_id:id-$3 De", html)
        self.assertIn("core/admin/google-name.js", html)

    def test_clicking_asks_for_that_venue_only(self):
        response = self.client.get(self.name_url(self.dewey))
        self.assertEqual(response.content.decode(), "Three Dollar Deweys")
        self.assertIn("no-store", response["Cache-Control"])
        self.place_name.assert_called_once_with("id-$3 Dewey's")

    def test_nothing_is_saved(self):
        before = Venue.objects.filter(pk=self.dewey.pk).values().get()
        self.client.get(self.name_url(self.dewey))
        self.client.get(reverse("admin:core_venue_change", args=[self.dewey.pk]))
        self.assertEqual(Venue.objects.filter(pk=self.dewey.pk).values().get(), before)

    def test_only_review_venues_are_looked_up(self):
        self.assertEqual(self.client.get(self.name_url(self.paradise)).status_code, 404)
        self.place_name.assert_not_called()

    def test_venue_page_shows_it_for_a_review_venue(self):
        html = self.client.get(reverse("admin:core_venue_change", args=[self.dewey.pk])).content.decode()
        self.assertIn("Three Dollar Deweys", html)
        self.client.get(reverse("admin:core_venue_change", args=[self.paradise.pk]))
        self.place_name.assert_called_once_with("id-$3 Dewey's")

    def test_failures_are_shown_without_the_key(self):
        self.place_name.side_effect = PlacesError("place details: HTTP 403")
        text = self.client.get(self.name_url(self.dewey)).content.decode()
        self.assertEqual(text, "couldn't ask google (place details: HTTP 403)")
        self.assertNotIn("SECRETKEY", text)

    def test_missing_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            text = self.client.get(self.name_url(self.dewey)).content.decode()
        self.assertEqual(text, "GOOGLE_PLACES_API_KEY isn't set")
        self.place_name.assert_not_called()

    def test_needs_an_admin(self):
        self.client.logout()
        response = self.client.get(self.name_url(self.dewey))
        self.assertEqual(response.status_code, 302)
        self.place_name.assert_not_called()


class SkipPlaceLookupAdminTestCase(TestCase):
    """"don't look up on google", for a venue with no single place (skip-place-lookup)"""

    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.porchfest = review(
            "Porchfest", ["name", "type"], 1.2, city_town="Somerville", state="MA",
            latitude=42.3876, longitude=-71.0995, place_latitude=42.3960, place_longitude=-71.1220,
        )
        self.event = Event.objects.create(title="porchfest", starttime=timezone.now() + datetime.timedelta(days=3), venue=self.porchfest)

    def act(self, action, venue, query="?place_lookup_status__exact=review"):
        # as from the review list, whose filter a cleared venue no longer matches
        url = reverse("admin:core_venue_changelist") + query
        return self.client.post(url, {"action": action, "_selected_action": [venue.pk]}, follow=True)

    def test_marking_a_festival(self):
        response = self.act("skip_place_lookup", self.porchfest)
        messages = [str(m) for m in response.context["messages"]]
        self.assertEqual(messages, ["1 venue won't be looked up on Google. Clear their lookup to undo."])
        venue = Venue.objects.get(pk=self.porchfest.pk)
        self.assertEqual(venue.place_lookup_status, Status.SKIPPED)
        self.assertEqual(
            (venue.place_id, venue.place_latitude, venue.place_longitude, venue.place_looked_up_at),
            ("", None, None, None),
        )
        self.assertEqual((venue.place_review_reasons, venue.place_distance_km), ([], None))
        self.assertEqual(venue.exact_location, (42.3876, -71.0995))
        # the event's stored map pin is the sheet's
        html = Event.all_objects.get(pk=self.event.pk).baked_html_template
        self.assertIn('data-venue-lnglat="-71.0995,42.3876"', html)

    def test_undoing_it(self):
        self.act("skip_place_lookup", self.porchfest)
        self.act("clear_place_lookup", self.porchfest, query="?place_lookup_status__exact=skipped")
        self.assertEqual(Venue.objects.get(pk=self.porchfest.pk).place_lookup_status, "")

    def test_filtering(self):
        Venue.objects.create(name="The Sinclair", place_lookup_status=Status.CONFIDENT)
        self.act("skip_place_lookup", self.porchfest)
        response = self.client.get(reverse("admin:core_venue_changelist") + "?place_lookup_status__exact=skipped")
        self.assertEqual([v.name for v in response.context["cl"].result_list], ["Porchfest"])
        self.assertContains(response, "Not looked up (no single place)")
