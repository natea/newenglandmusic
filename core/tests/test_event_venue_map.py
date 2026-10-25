from core.models import Event, Venue
from core.utils_event_caching import bake_event_html
from django.test import TestCase
from django.utils import timezone


class EventVenueMapTestCase(TestCase):
    def event_html(self, **venue_fields):
        venue = Venue.objects.create(
            name="Paradise Rock Club",
            latitude=42.3529,
            longitude=-71.1321,
            place_latitude=42.3519,
            place_longitude=-71.1195,
            place_maps_url="https://maps.google.com/?cid=123",
            **venue_fields,
        )
        event = Event.objects.create(title="show", starttime=timezone.now(), venue=venue)
        return bake_event_html(event)

    def test_confident_place_location_is_used(self):
        html = self.event_html(place_lookup_status=Venue.PlaceLookupStatus.CONFIDENT)
        self.assertIn('data-venue-lnglat="-71.1195,42.3519"', html)
        self.assertIn('href="https://maps.google.com/?cid=123"', html)

    def test_place_needing_review_is_not_used(self):
        html = self.event_html(place_lookup_status=Venue.PlaceLookupStatus.REVIEW)
        self.assertIn('data-venue-lnglat="-71.1321,42.3529"', html)
        self.assertIn("query=42.3529,-71.1321", html)
        self.assertNotIn("cid=123", html)

    def test_venue_without_coordinates_has_no_pin(self):
        venue = Venue.objects.create(name="Nowhere")
        event = Event.objects.create(title="show", starttime=timezone.now(), venue=venue)
        self.assertNotIn("data-venue-lnglat", bake_event_html(event))
