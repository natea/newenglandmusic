from core.neighborhoods import (
    NOMINATIM_SECONDS_BETWEEN_REQUESTS,
    OverpassUnavailable,
    accepted_result,
    choose_name,
    usable,
)
from core.tests.osm_fixture import FakeOsm, fixture, response
from django.test import SimpleTestCase


class NameRulesTestCase(SimpleTestCase):
    def test_neighbourhood_preferred(self):
        address = fixture("century.json")[0]["address"]
        self.assertEqual(choose_name(address, "Philadelphia"), "Grays Ferry")

    def test_community_board_skipped(self):
        address = {"neighbourhood": "Manhattan Community Board 3", "suburb": "Manhattan", "city": "New York"}
        self.assertIsNone(choose_name(address, "New York"))

    def test_historic_district_skipped(self):
        address = fixture("cafe_nine.json")[0]["address"]
        self.assertEqual(choose_name(address, "New Haven"), "Dixwell")

    def test_only_the_borough(self):
        address = fixture("eighteenth_ward.json")[0]["address"]
        self.assertIsNone(choose_name(address, "Brooklyn"))

    def test_unusable_names(self):
        for name in ("Boston", "Kings County", "Queens", "Ninth Square Historic District", "Main Street Historic District No. 2", "", None):
            with self.subTest(name):
                self.assertFalse(usable(name, "Boston"))
        self.assertTrue(usable("West End", "Boston"))


class SearchTestCase(SimpleTestCase):
    def test_venue_found(self):
        results = fixture("big_night_live.json")
        found = accepted_result(results, "Big Night Live", "Boston", "MA")
        self.assertEqual(choose_name(found["address"], "Boston"), "West End")

    def test_a_different_place_with_the_towns_name(self):
        self.assertIsNone(accepted_result(fixture("bus_stop_cambridge.json"), "The Sinclair", "Cambridge", "MA"))

    def test_wrong_state(self):
        self.assertIsNone(accepted_result(fixture("big_night_live.json"), "Big Night Live", "Boston", "NH"))

    def test_brooklyn_venue_is_in_its_borough(self):
        found = accepted_result(fixture("eighteenth_ward.json"), "18th Ward Brewing", "Brooklyn", "NY")
        self.assertIsNotNone(found)

    def test_paced_with_the_contact_user_agent(self):
        osm = FakeOsm(searches={"Big Night Live": fixture("big_night_live.json")})
        client = osm.client()
        for _ in range(3):
            client.search("Big Night Live", "Boston", "MA")
        self.assertEqual(osm.sleeps, [NOMINATIM_SECONDS_BETWEEN_REQUESTS] * 2)
        self.assertTrue(all("venue-db-event-check/1.0" in r.headers["User-Agent"] for r in osm.requests))
        self.assertEqual(osm.requests[0].params["q"], "Big Night Live, Boston, MA")


class OverpassTestCase(SimpleTestCase):
    def test_williamsburg(self):
        osm = FakeOsm(overpass=[fixture("overpass_williamsburg.json")])
        self.assertEqual(osm.client().nearest_neighborhood(40.7152, -73.9445, "Brooklyn"), "Williamsburg")
        self.assertIn("around:1500,40.7152,-73.9445", osm.overpass_requests[0].data["data"])

    def test_overpass_busy(self):
        osm = FakeOsm(overpass=[response(504)])
        with self.assertRaises(OverpassUnavailable):
            osm.client().nearest_neighborhood(40.7152, -73.9445, "Brooklyn")
        # four tries on each of the two servers
        self.assertEqual(len(osm.overpass_requests), 8)
        self.assertEqual(osm.sleeps, [5, 15, 45, 5, 15, 45])

    def test_busy_then_answers(self):
        osm = FakeOsm(overpass=[response(429), fixture("overpass_williamsburg.json")])
        self.assertEqual(osm.client().nearest_neighborhood(40.7152, -73.9445, "Brooklyn"), "Williamsburg")
