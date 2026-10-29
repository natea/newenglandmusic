import os
from unittest import mock

from core.models import Venue
from core.places import PlacesClient, PlacesError
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

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
        Venue.objects.create(name="Paradise Rock Club", place_lookup_status=Status.CONFIDENT)

    def changelist(self, query=""):
        return self.client.get(reverse("admin:core_venue_changelist") + query)

    def test_why_a_venue_needs_review(self):
        html = self.changelist("?place_lookup_status__exact=review").content.decode()
        self.assertIn("name differs · 0.4 km away", html)
        self.assertIn("in another state · 38.2 km away (over 25)", html)
        self.assertIn("not recorded (run lookup_venue_places --review)", html)

    def test_filter_by_reason(self):
        names = {v.name for v in self.changelist("?review_reason=state").context["cl"].result_list}
        self.assertEqual(names, {"Merriweather Post Pavilion"})
        names = {v.name for v in self.changelist("?review_reason=name").context["cl"].result_list}
        self.assertEqual(names, {"$3 Dewey's"})

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
