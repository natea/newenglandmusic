from core.models import Venue
from django.test import TestCase


class VenueLocationTestCase(TestCase):
    def test_location_is_city_and_state(self):
        venue = Venue(name="The Middle East", city_town="Cambridge", state="MA")
        self.assertEqual(venue.location, "Cambridge, MA")

    def test_location_leaves_out_missing_parts(self):
        self.assertEqual(Venue(name="v", state="VT").location, "VT")
        self.assertEqual(Venue(name="v", city_town="Burlington").location, "Burlington")
        self.assertEqual(Venue(name="v").location, "")


class VenueGoogleMapsLinkTestCase(TestCase):
    def test_link_uses_coordinates(self):
        venue = Venue(name="v", latitude=42.3634, longitude=-71.1013)
        self.assertEqual(
            venue.google_maps_link,
            "https://www.google.com/maps/search/?api=1&query=42.3634,-71.1013",
        )

    def test_zero_coordinates_still_make_a_link(self):
        venue = Venue(name="v", latitude=0.0, longitude=0.0)
        self.assertIn("query=0.0,0.0", venue.google_maps_link)

    def test_no_link_without_both_coordinates(self):
        self.assertEqual(Venue(name="v").google_maps_link, "")
        self.assertEqual(Venue(name="v", latitude=42.0).google_maps_link, "")
        self.assertEqual(Venue(name="v", longitude=-71.0).google_maps_link, "")
