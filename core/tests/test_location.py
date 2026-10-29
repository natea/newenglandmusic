from types import SimpleNamespace

from core.location import Location, decode, encode, format_miles, location_from_request, miles, resolve
from core.models import Venue
from core.tests.census_fixture import census_places
from django.test import SimpleTestCase, TestCase


class ResolveTestCase(TestCase):
    def setUp(self):
        census_places()
        for state in ("MA", "VT", "NJ", "CT"):
            Venue.objects.create(name=f"a venue in {state}", state=state)

    def test_zip_code(self):
        self.assertEqual(resolve("02144"), Location("02144", 42.4, -71.123))

    def test_town_and_state(self):
        for text in ("somerville, ma", "Somerville, MA", "Somerville, Massachusetts", " Somerville ,  massachusetts "):
            with self.subTest(text):
                self.assertEqual(resolve(text), Location("Somerville, MA", 42.39, -71.101))

    def test_town_name_only(self):
        # hamden is in CT and NY, and the site only has venues in CT
        self.assertEqual(resolve("Hamden"), Location("Hamden, CT", 41.397, -72.922))

    def test_town_with_venues_preferred(self):
        # somerville is in MA and ME, both covered, but only MA's has a venue
        Venue.objects.create(name="Aeronaut", state="MA", city_town="Somerville")
        Venue.objects.create(name="a maine venue", state="ME", city_town="Portland")
        self.assertEqual(resolve("Somerville"), Location("Somerville, MA", 42.39, -71.101))

    def test_several_towns_with_the_name(self):
        choices = resolve("Springfield")
        self.assertEqual([c.label for c in choices], ["Springfield, MA", "Springfield, NJ", "Springfield, VT"])

    def test_not_found(self):
        for text in ("99999", "Xyzzyville", "Somerville, ZZ", "", "   "):
            with self.subTest(text):
                self.assertIsNone(resolve(text))


class CookieTestCase(SimpleTestCase):
    def test_round_trip_rounds_to_about_100_metres(self):
        value = encode(Location("Somerville, MA", 42.390445, -71.101033))
        self.assertEqual(decode(value), Location("Somerville, MA", 42.39, -71.101))
        self.assertIn("42.390", value)

    def test_bad_values(self):
        for value in (None, "", "nonsense", "x|200|0", "|1|1", "label|a|b"):
            with self.subTest(value):
                self.assertIsNone(decode(value))

    def test_read_once_per_request(self):
        request = SimpleNamespace(COOKIES={"near": encode(Location("02144", 42.4, -71.123))})
        self.assertEqual(location_from_request(request).label, "02144")
        request.COOKIES = {}
        self.assertEqual(location_from_request(request).label, "02144")
        self.assertIsNone(location_from_request(None))


class DistanceTestCase(SimpleTestCase):
    def test_haversine(self):
        # boston city hall to the vermont state house in montpelier: about 153 miles in a straight line
        self.assertAlmostEqual(miles((42.3603, -71.0580), (44.2623, -72.5809)), 152.6, delta=1.5)
        self.assertEqual(miles((42.0, -71.0), (42.0, -71.0)), 0)

    def test_format(self):
        for distance, label in (
            (0.04, "less than 0.1 mi away"), (0.47, "0.5 mi away"), (9.94, "9.9 mi away"),
            (9.96, "10 mi away"), (143.6, "144 mi away"),
        ):
            with self.subTest(distance):
                self.assertEqual(format_miles(distance), label)
