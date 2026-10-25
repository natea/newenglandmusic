import json
from pathlib import Path
from unittest import mock

import requests
from core import places
from django.test import SimpleTestCase

FIXTURES = Path(__file__).parent / "fixtures" / "places"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def response(status=200, data=None):
    r = mock.Mock(status_code=status)
    r.json.return_value = data if data is not None else {}
    return r


class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def client_with(*responses):
    session = mock.Mock()
    session.post.side_effect = list(responses)
    clock = FakeClock()
    client = places.PlacesClient("SECRETKEY", session=session, sleep=clock.sleep, clock=clock.clock)
    return client, session, clock


class SearchPlaceTestCase(SimpleTestCase):
    def test_request_and_recorded_result(self):
        client, session, _ = client_with(response(200, load("paradise")))
        [place] = client.search_place("Paradise Rock Club, Allston, MA", 42.3529, -71.1321)

        self.assertEqual(session.post.call_args.args[0], places.SEARCH_URL)
        body = session.post.call_args.kwargs["json"]
        self.assertEqual(body["textQuery"], "Paradise Rock Club, Allston, MA")
        self.assertEqual(body["pageSize"], 3)
        circle = body["locationBias"]["circle"]
        self.assertEqual(circle["center"], {"latitude": 42.3529, "longitude": -71.1321})
        self.assertEqual(circle["radius"], 30_000)
        headers = session.post.call_args.kwargs["headers"]
        self.assertEqual(headers["X-Goog-Api-Key"], "SECRETKEY")

        self.assertEqual(place["id"], "ChIJ4U6oQOh544kROegfjmsLBCs")
        self.assertEqual(place["name"], "Paradise Rock Club")
        self.assertEqual(place["address"], "967 Commonwealth Ave, Boston, MA 02215, USA")
        self.assertEqual(place["state"], "MA")
        self.assertAlmostEqual(place["latitude"], 42.3518, places=3)
        self.assertEqual(place["business_status"], "OPERATIONAL")
        self.assertTrue(place["maps_url"].startswith("https://maps.google.com/?cid="))
        self.assertEqual((place["website"], place["phone"]), ("", ""))

    def test_pro_fields_only_by_default(self):
        client, session, _ = client_with(response(), response())
        client.search_place("x")
        mask = session.post.call_args.kwargs["headers"]["X-Goog-FieldMask"]
        self.assertIn("places.location", mask)
        self.assertNotIn("websiteUri", mask)
        self.assertNotIn("nationalPhoneNumber", mask)

        client.search_place("x", contact=True)
        mask = session.post.call_args.kwargs["headers"]["X-Goog-FieldMask"]
        self.assertIn("places.websiteUri", mask)
        self.assertIn("places.nationalPhoneNumber", mask)

    def test_no_bias_without_coordinates(self):
        client, session, _ = client_with(response())
        self.assertEqual(client.search_place("Somewhere, VT"), [])
        self.assertNotIn("locationBias", session.post.call_args.kwargs["json"])

    def test_requests_are_spaced_out(self):
        client, _, clock = client_with(response(), response())
        client.search_place("a")
        client.search_place("b")
        [wait] = clock.sleeps
        self.assertAlmostEqual(wait, places.MIN_SECONDS_BETWEEN_REQUESTS)

    def test_retry_then_success(self):
        client, session, _ = client_with(response(429), response(200, load("aura")))
        [place] = client.search_place("Aura, Portland, ME")
        self.assertEqual(place["name"], "Aura")
        self.assertEqual(session.post.call_count, 2)

    def test_repeated_failure(self):
        client, session, _ = client_with(response(500), response(503), response(502))
        with self.assertRaisesMessage(places.PlacesError, "places search: HTTP 502"):
            client.search_place("x")
        self.assertEqual(session.post.call_count, places.MAX_RETRIES + 1)

    def test_bad_request_is_not_retried(self):
        client, session, _ = client_with(response(403))
        with self.assertRaisesMessage(places.PlacesError, "HTTP 403"):
            client.search_place("x")
        self.assertEqual(session.post.call_count, 1)

    def test_errors_never_include_the_key(self):
        error = requests.ConnectionError("X-Goog-Api-Key: SECRETKEY refused")
        client, _, _ = client_with(error, error, error)
        with self.assertRaises(places.PlacesError) as raised:
            client.search_place("x")
        self.assertNotIn("SECRETKEY", str(raised.exception))

    def test_place_without_optional_fields(self):
        self.assertEqual(
            places.to_place_dict({"id": "p"}),
            {
                "id": "p",
                "name": "",
                "address": "",
                "state": "",
                "latitude": None,
                "longitude": None,
                "business_status": "",
                "maps_url": "",
                "website": "",
                "phone": "",
            },
        )
