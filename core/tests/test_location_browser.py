"""
the location form in a real browser. "use my location" gets its position from playwright's
emulated geolocation, so no location service is asked; every request that isn't to the
test server is aborted (core/tests/browser.py).
"""

import datetime

from core.models import Event, Venue
from core.tests.browser import BrowserTestCase
from core.tests.census_fixture import census_places
from django.utils import timezone


class LocationBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        census_places()
        venue = Venue.objects.create(name="Near Hall", state="MA", latitude=42.4068, longitude=-71.1224)
        Event.objects.create(title="near show", starttime=timezone.now() + datetime.timedelta(days=1), venue=venue)

    def context(self, **options):
        context = self.browser.new_context(**options)
        self.addCleanup(context.close)
        context.route("**/*", self.only_the_test_server)
        return context

    def test_typed_location_shows_labels(self):
        _, page = self.open_page("/", context=self.context())
        page.fill('form.locationForm input[name="q"]', "02144")
        page.click('form.locationForm button[type="submit"]')
        page.wait_for_selector(".event-distance")
        self.assertEqual(page.locator(".event-distance").first.inner_text(), "(0.5 mi away)")
        self.assertIn("02144", page.locator(".location-current").inner_text())

    def test_device_location(self):
        context = self.context(geolocation={"latitude": 42.39613, "longitude": -71.12212}, permissions=["geolocation"])
        _, page = self.open_page("/", context=context)
        page.click("form.locationForm .use-my-location")
        page.wait_for_selector(".event-distance")
        self.assertIn("your location", page.locator(".location-current").inner_text())
        cookie = next(c for c in context.cookies() if c["name"] == "near")
        self.assertIn("42.396", cookie["value"])
        self.assertIn("-71.122", cookie["value"])

    def test_position_refused(self):
        _, page = self.open_page("/", context=self.context(permissions=[]))
        page.click("form.locationForm .use-my-location")
        page.wait_for_selector("text=didn't give a location")
        self.assertEqual(page.locator(".event-distance").count(), 0)

    def test_suggestions_fill_as_you_type(self):
        _, page = self.open_page("/", context=self.context())
        page.type('form.locationForm input[name="q"]', "som", delay=30)
        page.wait_for_function("() => document.querySelectorAll('#location-suggestions option').length > 0")
        options = page.eval_on_selector_all("#location-suggestions option", "els => els.map(e => e.value)")
        self.assertIn("Somerville, MA", options)
