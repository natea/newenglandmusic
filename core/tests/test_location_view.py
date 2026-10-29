from core.location import COOKIE_NAME, decode
from core.models import Venue
from core.tests.census_fixture import census_places
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext


class LocationViewTestCase(TestCase):
    def setUp(self):
        census_places()
        for state in ("MA", "VT", "NJ", "CT"):
            Venue.objects.create(name=f"a venue in {state}", state=state)

    def test_typed_location(self):
        response = self.client.get("/location", {"q": "02144", "next": "/2026-11/"})
        self.assertRedirects(response, "/2026-11/", fetch_redirect_response=False)
        self.assertEqual(decode(response.cookies[COOKIE_NAME].value).label, "02144")

    def test_device_location(self):
        response = self.client.get("/location", {"lat": "42.39613", "lon": "-71.12212", "next": "/"})
        location = decode(response.cookies[COOKIE_NAME].value)
        self.assertEqual((location.label, location.latitude, location.longitude), ("your location", 42.396, -71.122))

    def test_position_refused(self):
        response = self.client.get("/location", {"error": "position", "next": "/"}, follow=True)
        self.assertContains(response, "didn&#x27;t give a location")
        self.assertNotIn(COOKIE_NAME, self.client.cookies)

    def test_several_matches_offered(self):
        response = self.client.get("/location", {"q": "Springfield", "next": "/"})
        self.assertEqual(response.status_code, 200)
        for label in ("Springfield, MA", "Springfield, VT", "Springfield, NJ"):
            self.assertContains(response, label)
        self.assertNotIn(COOKIE_NAME, response.cookies)

    def test_not_found(self):
        response = self.client.get("/location", {"q": "Xyzzyville", "next": "/"}, follow=True)
        self.assertContains(response, "couldn&#x27;t find")
        self.assertNotIn(COOKIE_NAME, response.cookies)

    def test_clearing(self):
        self.client.get("/location", {"q": "02144"})
        response = self.client.get("/location", {"clear": "1", "next": "/"})
        self.assertEqual(response.cookies[COOKIE_NAME].value, "")

    def test_outside_next_refused(self):
        response = self.client.get("/location", {"q": "02144", "next": "https://evil.example/"})
        self.assertEqual(response["Location"], "/")

    def test_not_stored_on_the_server(self):
        with CaptureQueriesContext(connection) as queries:
            self.client.get("/location", {"q": "Somerville, MA"})
        self.assertFalse([q for q in queries.captured_queries if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE"))])
