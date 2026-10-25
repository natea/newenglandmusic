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


class VenueExactLocationTestCase(TestCase):
    def venue(self, status="", **fields):
        defaults = dict(
            name="v",
            latitude=42.35,
            longitude=-71.13,
            place_lookup_status=status,
            place_latitude=42.3519,
            place_longitude=-71.1195,
            place_maps_url="https://maps.google.com/?cid=123",
        )
        return Venue(**{**defaults, **fields})

    def test_confident_place_is_used(self):
        venue = self.venue(Venue.PlaceLookupStatus.CONFIDENT)
        self.assertEqual(venue.exact_location, (42.3519, -71.1195))
        self.assertEqual(venue.google_maps_link, "https://maps.google.com/?cid=123")

    def test_confident_place_without_maps_url_links_to_its_coordinates(self):
        venue = self.venue(Venue.PlaceLookupStatus.CONFIDENT, place_maps_url="")
        self.assertIn("query=42.3519,-71.1195", venue.google_maps_link)

    def test_unconfirmed_place_is_not_used(self):
        for status in ("", Venue.PlaceLookupStatus.REVIEW, Venue.PlaceLookupStatus.NOT_FOUND):
            venue = self.venue(status)
            self.assertEqual(venue.exact_location, (42.35, -71.13), status)
            self.assertIn("query=42.35,-71.13", venue.google_maps_link, status)

    def test_no_coordinates_at_all(self):
        self.assertEqual(Venue(name="v").exact_location, (None, None))
        self.assertEqual(Venue(name="v").google_maps_link, "")
