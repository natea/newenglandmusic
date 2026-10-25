import copy
import datetime
import json
from pathlib import Path
from unittest import mock

import requests
from core.event_fetching import ticketmaster as tm
from django.test import SimpleTestCase
from django.utils import timezone

FIXTURES = Path(__file__).parent / "fixtures" / "ticketmaster"


def load(name):
    return json.loads((FIXTURES / name).read_text())


def response(status=200, data=None):
    r = mock.Mock(status_code=status)
    r.json.return_value = data if data is not None else {}
    return r


def local(*args):
    return timezone.make_aware(datetime.datetime(*args))


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
    client = tm.TicketmasterClient("SECRETKEY", session=session, sleep=clock.sleep, clock=clock.clock)
    return client, session, clock


class ClientTestCase(SimpleTestCase):
    def test_success(self):
        client, session, _ = client_with(response(200, {"ok": True}))
        self.assertEqual(client.get("events.json", venueId="v1"), {"ok": True})
        url = session.get.call_args.args[0]
        params = session.get.call_args.kwargs["params"]
        self.assertEqual(url, "https://app.ticketmaster.com/discovery/v2/events.json")
        self.assertEqual(params, {"apikey": "SECRETKEY", "venueId": "v1"})

    def test_requests_are_spaced_out(self):
        client, _, clock = client_with(response(), response(), response())
        for _ in range(3):
            client.get("venues.json")
        # the clock doesn't move between calls, so each later call waits the full gap
        self.assertEqual(clock.sleeps, [tm.MIN_SECONDS_BETWEEN_REQUESTS] * 2)
        self.assertLessEqual(1 / tm.MIN_SECONDS_BETWEEN_REQUESTS, 5)

    def test_rate_limited_then_success(self):
        client, session, clock = client_with(response(429), response(200, {"ok": True}))
        self.assertEqual(client.get("events.json"), {"ok": True})
        self.assertEqual(session.get.call_count, 2)
        # backed off before retrying
        self.assertIn(1, clock.sleeps)

    def test_repeated_server_errors_fail_after_retries(self):
        client, session, _ = client_with(response(503), response(502), response(500))
        with self.assertRaisesMessage(tm.TicketmasterError, "events.json: HTTP 500"):
            client.get("events.json")
        self.assertEqual(session.get.call_count, tm.MAX_RETRIES + 1)

    def test_client_errors_are_not_retried(self):
        client, session, _ = client_with(response(401))
        with self.assertRaisesMessage(tm.TicketmasterError, "HTTP 401"):
            client.get("events.json")
        self.assertEqual(session.get.call_count, 1)

    def test_errors_never_include_the_key(self):
        error = requests.ConnectionError(
            "failed: https://app.ticketmaster.com/discovery/v2/events.json?apikey=SECRETKEY"
        )
        client, _, _ = client_with(error, error, error)
        with self.assertRaises(tm.TicketmasterError) as raised:
            client.get("events.json")
        self.assertNotIn("SECRETKEY", str(raised.exception))
        self.assertEqual(str(raised.exception), "events.json: ConnectionError")

    def test_venue_events_request(self):
        client, session, _ = client_with(response(200, load("paradise_events.json")))
        events = client.venue_events("KovZpZA11JtA")
        self.assertEqual(len(events), 3)
        params = session.get.call_args.kwargs["params"]
        self.assertEqual(params["venueId"], "KovZpZA11JtA")
        self.assertEqual(params["sort"], "date,asc")
        self.assertEqual(params["size"], 50)
        # everything but resale ("tmr"); ticketweb is where some venues sell most shows
        self.assertEqual(params["source"], "ticketmaster,universe,frontgate,ticketweb")
        self.assertRegex(params["startDateTime"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_venue_without_events(self):
        client, _, _ = client_with(response(200, {"page": {"totalElements": 0}}))
        self.assertEqual(client.venue_events("v1"), [])

    def test_search_venues(self):
        client, session, _ = client_with(response(200, load("paradise_venues.json")))
        venues = client.search_venues("Paradise Rock Club", "MA")
        self.assertEqual(session.get.call_args.kwargs["params"]["stateCode"], "MA")
        self.assertEqual(
            venues[0],
            {
                "id": "KovZpZA11JtA",
                "name": "Paradise Rock Club presented by Citizens",
                "address": "967 Commonwealth Avenue",
                "city": "Boston",
                "state": "MA",
                "latitude": 42.3518332,
                "longitude": -71.1195379,
            },
        )
        # a listing without coordinates
        self.assertIsNone(venues[1]["latitude"])


class ToEventDictTestCase(SimpleTestCase):
    def setUp(self):
        self.events = load("paradise_events.json")["_embedded"]["events"]

    def event(self, index=0, **changes):
        event = copy.deepcopy(self.events[index])
        event.update(changes)
        return event

    def test_recorded_event(self):
        data = tm.to_event_dict(self.event())
        self.assertEqual(data["title"], "Holywatr: Deo Gratias Tour")
        # the headliner is in the title, so only the support act is listed
        self.assertEqual(data["artists"], "Mercury")
        self.assertEqual(data["starttime"], local(2026, 10, 25, 19, 0))
        self.assertFalse(data["all_day"])
        self.assertTrue(data["hyperlink"].startswith("https://www.ticketmaster.com/"))
        self.assertEqual(data["ticket_hyperlink"], data["hyperlink"])
        self.assertTrue(data["description"].startswith("THIS EVENT IS ALL AGES."))
        self.assertIsNone(data["price_amount"])
        self.assertFalse(data["is_cancelled"])
        self.assertEqual(data["external_id"], "tm:vvG17Z_G29M9oz")

    def test_headliner_matched_regardless_of_case(self):
        data = tm.to_event_dict(self.event(1))
        self.assertEqual(data["title"], "THE ARMY, THE NAVY: THE FAKE BRAVE TOUR 2026")
        self.assertEqual(data["artists"], "Ella Woolsey")

    def test_headliner_and_support(self):
        event = self.event(
            name="Samantha Fish",
            priceRanges=[{"type": "standard", "currency": "USD", "min": 35.0, "max": 55.0}],
            _embedded={"attractions": [{"name": "Samantha Fish"}, {"name": "Sgt. Splendor"}]},
        )
        data = tm.to_event_dict(event)
        self.assertEqual(data["title"], "Samantha Fish")
        self.assertEqual(data["artists"], "Sgt. Splendor")
        self.assertEqual(data["price_amount"], 35.0)

    def test_lowest_price_wins(self):
        event = self.event(priceRanges=[{"min": 40.0}, {"min": 25.5}, {"max": 10.0}])
        self.assertEqual(tm.to_event_dict(event)["price_amount"], 25.5)

    def test_time_not_announced(self):
        event = self.event()
        event["dates"]["start"].update(timeTBA=True)
        data = tm.to_event_dict(event)
        self.assertTrue(data["all_day"])
        self.assertEqual(data["starttime"], local(2026, 10, 25))

        event = self.event()
        event["dates"]["start"] = {"localDate": "2026-11-05", "noSpecificTime": True}
        self.assertTrue(tm.to_event_dict(event)["all_day"])

    def test_local_time_used_without_exact_datetime(self):
        event = self.event()
        event["dates"]["start"] = {"localDate": "2026-11-05", "localTime": "20:30:00"}
        self.assertEqual(tm.to_event_dict(event)["starttime"], local(2026, 11, 5, 20, 30))

    def test_cancelled(self):
        event = self.event()
        event["dates"]["status"]["code"] = "canceled"
        self.assertTrue(tm.to_event_dict(event)["is_cancelled"])

    def test_rescheduled_uses_the_new_date(self):
        event = self.event()
        event["dates"]["status"]["code"] = "rescheduled"
        event["dates"]["start"].update(
            localDate="2026-12-01", localTime="20:00:00", dateTime="2026-12-02T01:00:00Z"
        )
        data = tm.to_event_dict(event)
        self.assertEqual(data["starttime"], local(2026, 12, 1, 20, 0))
        self.assertFalse(data["is_cancelled"])
        self.assertEqual(data["external_id"], "tm:vvG17Z_G29M9oz")

    def test_postponed_without_a_date_is_skipped(self):
        event = self.event()
        event["dates"]["status"]["code"] = "postponed"
        event["dates"]["start"] = {"dateTBD": True}
        self.assertIsNone(tm.to_event_dict(event))

    def test_non_music_and_test_events_are_skipped(self):
        for segment in ("Arts & Theatre", "Sports", "Undefined"):
            event = self.event()
            event["classifications"][0]["segment"]["name"] = segment
            self.assertIsNone(tm.to_event_dict(event), segment)
        self.assertIsNone(tm.to_event_dict(self.event(classifications=[])))
        self.assertIsNone(tm.to_event_dict(self.event(test=True)))

    def test_description_falls_back_to_please_note(self):
        event = self.event()
        del event["info"]
        self.assertEqual(tm.to_event_dict(event)["description"], "THIS EVENT IS ALL AGES.")
        del event["pleaseNote"]
        self.assertEqual(tm.to_event_dict(event)["description"], "")
