import datetime

from core.location import COOKIE_NAME, Location, encode
from core.models import Event, Venue
from core.saved_shows import COOKIE_NAME as SAVED_COOKIE
from core.saved_shows import format_saved
from django.test import TestCase
from django.utils import timezone

# zip 02144's point, and venues 0.47 and 148 miles from it (sheet coordinates, no places match)
HERE = Location("02144", 42.4, -71.123)


class DistanceLabelTestCase(TestCase):
    def setUp(self):
        tomorrow = timezone.now() + datetime.timedelta(days=1)
        self.near = Venue.objects.create(name="Near Hall", latitude=42.4068, longitude=-71.1224)
        self.far = Venue.objects.create(name="Far Barn", latitude=44.2623, longitude=-72.5809)
        self.nowhere = Venue.objects.create(name="Unplaced")
        self.near_show = Event.objects.create(title="near show", starttime=tomorrow, venue=self.near)
        self.far_show = Event.objects.create(title="far show", starttime=tomorrow + datetime.timedelta(hours=1), venue=self.far)
        self.unplaced_show = Event.objects.create(title="unplaced show", starttime=tomorrow + datetime.timedelta(hours=2), venue=self.nowhere)
        self.override_show = Event.objects.create(
            title="basement show", starttime=tomorrow + datetime.timedelta(hours=3), venue=self.near, venue_override="a basement"
        )

    def page(self, url="/", location=HERE):
        if location:
            self.client.cookies[COOKIE_NAME] = encode(location)
        return self.client.get(url).content.decode()

    def block(self, html, event):
        start = html.index(f'id="event-{event.pk}"')
        return html[start:html.find('id="event-', start + 10)]

    def test_distances_shown_in_time_order(self):
        html = self.page()
        self.assertIn("(0.5 mi away)", self.block(html, self.near_show))
        self.assertLess(html.index("near show"), html.index("far show"))

    def test_far_away(self):
        self.assertIn("(148 mi away)", self.block(self.page(), self.far_show))

    def test_no_coordinates(self):
        html = self.page()
        self.assertNotIn("mi away", self.block(html, self.unplaced_show))
        self.assertNotIn("mi away", self.block(html, self.override_show))

    def test_no_location(self):
        self.assertNotIn("mi away", self.page(location=None))

    def test_stored_html_unchanged(self):
        self.page()
        self.near_show.save()
        self.near_show.refresh_from_db()
        self.assertNotIn("mi away", self.near_show.baked_html_template)

    def test_saved_shows_page(self):
        self.client.cookies[SAVED_COOKIE] = format_saved([self.near_show.pk])
        self.assertIn("(0.5 mi away)", self.page("/saved"))
