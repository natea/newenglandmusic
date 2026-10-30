import copy
import datetime
import json
from pathlib import Path
from unittest import mock

import requests
from core.event_fetching import seatgeek as sg
from django.test import SimpleTestCase
from django.utils import timezone

# recorded from the real api on 2026-10-29, trimmed to a few events
FIXTURES = Path(__file__).parent / "fixtures" / "seatgeek"


def load(name):
    return json.loads((FIXTURES / name).read_text())


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
    session.get.side_effect = list(responses)
    clock = FakeClock()
    client = sg.SeatGeekClient("SECRETID", session=session, sleep=clock.sleep, clock=clock.clock)
    return client, session, clock


class ClientTestCase(SimpleTestCase):
    def test_client_id_is_sent_by_basic_auth_not_in_the_url(self):
        client, session, _ = client_with(response(200, {"ok": True}))
        self.assertEqual(client.get("events", per_page=1), {"ok": True})
        url = session.get.call_args.args[0]
        kwargs = session.get.call_args.kwargs
        self.assertEqual(url, "https://api.seatgeek.com/2/events")
        self.assertEqual(kwargs["params"], {"per_page": 1})
        self.assertEqual(kwargs["auth"], ("SECRETID", ""))
        self.assertEqual(kwargs["headers"]["User-Agent"], "venue-db-event-check/1.0")

    def test_requests_are_spaced_out(self):
        client, _, clock = client_with(response(), response(), response())
        for _ in range(3):
            client.get("venues")
        self.assertEqual(clock.sleeps, [sg.MIN_SECONDS_BETWEEN_REQUESTS] * 2)

    def test_rate_limited_then_success(self):
        client, session, clock = client_with(response(429), response(200, {"ok": True}))
        self.assertEqual(client.get("events"), {"ok": True})
        self.assertEqual(session.get.call_count, 2)
        self.assertIn(1, clock.sleeps)

    def test_repeated_server_errors_fail_after_retries(self):
        client, session, _ = client_with(response(503), response(502), response(500))
        with self.assertRaisesMessage(sg.SeatGeekError, "events: HTTP 500"):
            client.get("events")
        self.assertEqual(session.get.call_count, sg.MAX_RETRIES + 1)

    def test_client_errors_are_not_retried(self):
        client, session, _ = client_with(response(403))
        with self.assertRaisesMessage(sg.SeatGeekError, "HTTP 403"):
            client.get("events")
        self.assertEqual(session.get.call_count, 1)

    def test_errors_never_include_the_client_id(self):
        error = requests.ConnectionError("failed: https://SECRETID:@api.seatgeek.com/2/events")
        client, _, _ = client_with(error, error, error)
        with self.assertRaises(sg.SeatGeekError) as raised:
            client.get("events")
        self.assertNotIn("SECRETID", str(raised.exception))
        self.assertEqual(str(raised.exception), "events: ConnectionError")

    def test_venue_events_request(self):
        client, session, _ = client_with(response(200, load("events_sinclair.json")))
        events = client.venue_events("11280")
        self.assertEqual(len(events), 5)
        params = session.get.call_args.kwargs["params"]
        self.assertEqual(params["venue.id"], "11280")
        self.assertEqual(params["sort"], "datetime_utc.asc")
        self.assertEqual(params["per_page"], 100)
        self.assertRegex(params["datetime_utc.gte"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$")

    def test_venue_without_events(self):
        client, _, _ = client_with(response(200, {"events": [], "meta": {"total": 0}}))
        self.assertEqual(client.venue_events("1"), [])

    def test_search_venues(self):
        client, session, _ = client_with(response(200, load("venues_toads.json")))
        venues = client.search_venues("Toads Place", "CT")
        params = session.get.call_args.kwargs["params"]
        self.assertEqual((params["q"], params["state"]), ("Toads Place", "CT"))
        self.assertEqual(
            venues[0],
            {
                "id": "1075",
                "name": "Toad's Place",
                "address": "300 York Street",
                "city": "New Haven",
                "state": "CT",
                "latitude": 41.308,
                "longitude": -72.9244,
                "upcoming_events": 12,
            },
        )
        self.assertEqual(venues[1]["name"], "Lilly's Pad (Toad's Place Upstairs)")
        self.assertEqual(venues[1]["upcoming_events"], 0)


class ToEventDictTestCase(SimpleTestCase):
    def setUp(self):
        self.events = load("events_sinclair.json")["events"]

    def event(self, index=0, **changes):
        return {**copy.deepcopy(self.events[index]), **changes}

    def test_recorded_concert(self):
        event = sg.to_event_dict(self.events[0], "https://www.sinclaircambridge.com/events")
        self.assertEqual(event["title"], "The Bad Plus")
        self.assertEqual(event["artists"], "")
        self.assertEqual(
            event["starttime"], datetime.datetime(2026, 11, 12, 1, 0, tzinfo=datetime.timezone.utc)
        )
        self.assertFalse(event["all_day"])
        self.assertEqual(event["external_id"], "seatgeek:18363578")
        self.assertIsNone(event["price_amount"])
        self.assertFalse(event["is_cancelled"])

    def test_links_to_the_given_ticket_page_never_to_seatgeek(self):
        event = sg.to_event_dict(self.events[0], "https://www.sinclaircambridge.com/events")
        self.assertEqual(event["hyperlink"], "https://www.sinclaircambridge.com/events")
        self.assertEqual(event["ticket_hyperlink"], "https://www.sinclaircambridge.com/events")
        self.assertNotIn("seatgeek.com", json.dumps(event, default=str))

    def test_without_a_ticket_page_the_links_are_empty(self):
        event = sg.to_event_dict(self.events[0])
        self.assertEqual((event["hyperlink"], event["ticket_hyperlink"]), ("", ""))

    def test_support_acts_not_in_the_title_are_artists(self):
        event = sg.to_event_dict(self.event(1, title="strongboi"))
        self.assertEqual(event["artists"], "Salami Rose Joe Louis")
        # both are in the recorded title, so neither is repeated
        self.assertEqual(sg.to_event_dict(self.events[1])["artists"], "")

    def test_comedy_dance_and_entertainment_are_skipped(self):
        self.assertEqual([sg.to_event_dict(e) is None for e in self.events], [False, False, True, True, True])

    def test_music_festivals_are_kept(self):
        event = self.event(taxonomies=[{"name": "music_festival"}])
        self.assertIsNotNone(sg.to_event_dict(event))

    def test_time_not_announced_is_all_day_on_the_local_date(self):
        event = sg.to_event_dict(self.event(time_tbd=True, datetime_local="2026-11-11T03:30:00"))
        self.assertTrue(event["all_day"])
        self.assertEqual(timezone.localtime(event["starttime"]).date(), datetime.date(2026, 11, 11))

    def test_date_not_announced_is_skipped(self):
        self.assertIsNone(sg.to_event_dict(self.event(date_tbd=True)))
        self.assertIsNone(sg.to_event_dict(self.event(datetime_tbd=True)))

    def test_cancelled(self):
        self.assertTrue(sg.to_event_dict(self.event(status="cancelled"))["is_cancelled"])
