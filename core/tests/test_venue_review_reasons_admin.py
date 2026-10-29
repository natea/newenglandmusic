from core.models import Venue
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
