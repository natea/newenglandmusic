import uuid

from core.models import Venue
from core.views.event_submission import UserSubmittedEventForm
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone


class VenuePickerTestCase(TestCase):
    def setUp(self):
        # a shared word in the names, so one search finds all three
        self.word = uuid.uuid4().hex[:8]
        self.active = Venue.objects.create(
            name=f"open {self.word}", city_town="Portland", state="ME", is_active=True
        )
        self.unknown = Venue.objects.create(name=f"maybe {self.word}", is_active=None)
        self.closed = Venue.objects.create(
            name=f"closed {self.word}", city_town="Albany", state="NY", is_active=False
        )

    def search(self, q):
        response = self.client.get(reverse("venue-autocomplete"), {"q": q})
        self.assertEqual(response.status_code, 200)
        return {result["id"]: result["text"] for result in response.json()["results"]}

    def test_autocomplete_leaves_out_inactive_venues(self):
        results = self.search(self.word)
        self.assertIn(str(self.active.pk), results)
        self.assertIn(str(self.unknown.pk), results)
        self.assertNotIn(str(self.closed.pk), results)

    def test_searching_for_a_closed_venue_finds_nothing(self):
        self.assertEqual(self.search(f"closed {self.word}"), {})

    def test_autocomplete_labels_venues_with_location(self):
        results = self.search(self.word)
        self.assertEqual(results[str(self.active.pk)], f"open {self.word} (Portland, ME)")
        # no location to show
        self.assertEqual(results[str(self.unknown.pk)], f"maybe {self.word}")

    def submit(self, venue):
        return UserSubmittedEventForm(
            dict(starttime=timezone.now(), title="show", venue=venue.pk)
        )

    def test_submission_form_accepts_active_and_unknown_venues(self):
        self.assertTrue(self.submit(self.active).is_valid())
        self.assertTrue(self.submit(self.unknown).is_valid())

    def test_submission_form_rejects_inactive_venue(self):
        form = self.submit(self.closed)
        self.assertFalse(form.is_valid())
        self.assertIn("venue", form.errors)
