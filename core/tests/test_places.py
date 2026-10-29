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
    session.request.side_effect = list(responses)
    clock = FakeClock()
    client = places.PlacesClient("SECRETKEY", session=session, sleep=clock.sleep, clock=clock.clock)
    return client, session, clock


class SearchPlaceTestCase(SimpleTestCase):
    def test_request_and_recorded_result(self):
        client, session, _ = client_with(response(200, load("paradise")))
        [place] = client.search_place("Paradise Rock Club, Allston, MA", 42.3529, -71.1321)

        self.assertEqual(session.request.call_args.args, ("POST", places.SEARCH_URL))
        body = session.request.call_args.kwargs["json"]
        self.assertEqual(body["textQuery"], "Paradise Rock Club, Allston, MA")
        self.assertEqual(body["pageSize"], 3)
        circle = body["locationBias"]["circle"]
        self.assertEqual(circle["center"], {"latitude": 42.3529, "longitude": -71.1321})
        self.assertEqual(circle["radius"], 30_000)
        headers = session.request.call_args.kwargs["headers"]
        self.assertEqual(headers["X-Goog-Api-Key"], "SECRETKEY")

        self.assertEqual(place["id"], "ChIJ4U6oQOh544kROegfjmsLBCs")
        self.assertEqual(place["name"], "Paradise Rock Club")
        self.assertEqual(place["address"], "967 Commonwealth Ave, Boston, MA 02215, USA")
        self.assertEqual(place["state"], "MA")
        self.assertAlmostEqual(place["latitude"], 42.3518, places=3)
        self.assertEqual(place["business_status"], "OPERATIONAL")

    def test_pro_fields_only(self):
        client, session, _ = client_with(response())
        client.search_place("x")
        mask = session.request.call_args.kwargs["headers"]["X-Goog-FieldMask"]
        self.assertIn("places.location", mask)
        # nothing the terms don't let us store, and nothing pricier
        for field in ("websiteUri", "nationalPhoneNumber", "googleMapsUri"):
            self.assertNotIn(field, mask)

    def test_no_bias_without_coordinates(self):
        client, session, _ = client_with(response())
        self.assertEqual(client.search_place("Somewhere, VT"), [])
        self.assertNotIn("locationBias", session.request.call_args.kwargs["json"])

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
        self.assertEqual(session.request.call_count, 2)

    def test_repeated_failure(self):
        client, session, _ = client_with(response(500), response(503), response(502))
        with self.assertRaisesMessage(places.PlacesError, "places search: HTTP 502"):
            client.search_place("x")
        self.assertEqual(session.request.call_count, places.MAX_RETRIES + 1)

    def test_bad_request_is_not_retried(self):
        client, session, _ = client_with(response(403))
        with self.assertRaisesMessage(places.PlacesError, "HTTP 403"):
            client.search_place("x")
        self.assertEqual(session.request.call_count, 1)

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
            },
        )


class PlaceDetailsTestCase(SimpleTestCase):
    def test_request_and_recorded_result(self):
        client, session, _ = client_with(response(200, load("details_paradise")))
        place = client.place_details("ChIJ4U6oQOh544kROegfjmsLBCs")
        self.assertEqual(
            session.request.call_args.args,
            ("GET", "https://places.googleapis.com/v1/places/ChIJ4U6oQOh544kROegfjmsLBCs"),
        )
        headers = session.request.call_args.kwargs["headers"]
        self.assertEqual(headers["X-Goog-FieldMask"], "id,location,businessStatus")
        self.assertEqual(headers["X-Goog-Api-Key"], "SECRETKEY")
        self.assertEqual(
            place,
            {
                "id": "ChIJ4U6oQOh544kROegfjmsLBCs",
                "latitude": 42.3518386,
                "longitude": -71.1194958,
                "business_status": "OPERATIONAL",
            },
        )

    def test_not_found_is_not_retried(self):
        client, session, _ = client_with(response(404))
        with self.assertRaisesMessage(places.PlaceNotFound, "place details: HTTP 404"):
            client.place_details("gone")
        self.assertEqual(session.request.call_count, 1)

    def test_retries_on_rate_limit_and_server_errors(self):
        client, session, _ = client_with(
            response(429), response(503), response(200, load("details_paradise"))
        )
        self.assertEqual(client.place_details("x")["business_status"], "OPERATIONAL")
        self.assertEqual(session.request.call_count, 3)

    def test_errors_never_include_the_key(self):
        error = requests.ConnectionError("X-Goog-Api-Key: SECRETKEY refused")
        client, _, _ = client_with(error, error, error)
        with self.assertRaises(places.PlacesError) as raised:
            client.place_details("x")
        self.assertNotIn("SECRETKEY", str(raised.exception))


class PlaceNameTestCase(SimpleTestCase):
    def test_asks_for_the_name_alone(self):
        client, session, _ = client_with(response(data={"displayName": {"text": "Three Dollar Deweys"}}))
        self.assertEqual(client.place_name("ChIJdewey"), "Three Dollar Deweys")
        args, kwargs = session.request.call_args
        self.assertEqual(args, ("GET", "https://places.googleapis.com/v1/places/ChIJdewey"))
        self.assertEqual(kwargs["headers"]["X-Goog-FieldMask"], "displayName")

    def test_place_without_a_name(self):
        client, _, _ = client_with(response(data={}))
        self.assertEqual(client.place_name("ChIJx"), "")
