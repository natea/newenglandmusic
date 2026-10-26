import datetime
import json
from pathlib import Path
from types import SimpleNamespace

from core.event_fetching.eventbrite import (
    EventbriteClient,
    EventbriteError,
    event_venue,
    find_eventbrite_ids,
    to_event_dict,
)
from django.test import SimpleTestCase

FIXTURES = Path(__file__).parent / "fixtures" / "eventbrite"


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


class FakeSession:
    """returns queued (status, json) responses and remembers each request"""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.requests.append(SimpleNamespace(url=url, params=params, headers=headers))
        status, data = self.responses.pop(0)
        return SimpleNamespace(status_code=status, json=lambda: data)


def client(*responses):
    session = FakeSession(*responses)
    return EventbriteClient("secret-token", session=session, sleep=lambda s: None), session


class ClientTestCase(SimpleTestCase):
    def test_event_gives_its_organizer(self):
        eventbrite, session = client((200, fixture("event.json")))
        self.assertEqual(eventbrite.event("707179501927")["organizer_id"], "20010471604")
        self.assertTrue(session.requests[0].url.endswith("/v3/events/707179501927/"))
        self.assertEqual(session.requests[0].headers, {"Authorization": "Bearer secret-token"})

    def test_organizer_events(self):
        eventbrite, session = client((200, fixture("organizer_events.json")))
        events = eventbrite.organizer_events("20010471604")
        self.assertEqual(len(events), 3)
        self.assertEqual(session.requests[0].params["status"], "live")
        self.assertIn("venue", session.requests[0].params["expand"])

    def test_organizer_events_follow_pages(self):
        first = {"events": [{"id": "1"}], "pagination": {"has_more_items": True, "continuation": "abc"}}
        second = {"events": [{"id": "2"}], "pagination": {"has_more_items": False}}
        eventbrite, session = client((200, first), (200, second))
        self.assertEqual([e["id"] for e in eventbrite.organizer_events("9")], ["1", "2"])
        self.assertEqual(session.requests[1].params["continuation"], "abc")

    def test_errors_never_include_the_token(self):
        eventbrite, _ = client((404, {}))
        with self.assertRaises(EventbriteError) as raised:
            eventbrite.event("1")
        self.assertEqual(str(raised.exception), "events/1/: HTTP 404")
        self.assertNotIn("secret-token", str(raised.exception))

    def test_retries_when_rate_limited(self):
        eventbrite, session = client((429, {}), (200, fixture("event.json")))
        self.assertEqual(eventbrite.event("707179501927")["id"], "707179501927")
        self.assertEqual(len(session.requests), 2)


class ToEventDictTestCase(SimpleTestCase):
    def setUp(self):
        self.events = fixture("organizer_events.json")["events"]

    def test_fields(self):
        event = to_event_dict(self.events[0])
        self.assertEqual(event["title"], "Hayley Jane Band")
        self.assertEqual(
            event["starttime"], datetime.datetime(2026, 10, 31, 1, 0, tzinfo=datetime.timezone.utc)
        )
        self.assertFalse(event["all_day"])
        self.assertEqual(event["price_amount"], 18.47)
        self.assertEqual(event["external_id"], "eventbrite:1998894231455")
        self.assertTrue(event["hyperlink"].startswith("https://www.eventbrite.com/e/"))
        self.assertEqual(event["ticket_hyperlink"], event["hyperlink"])

    def test_free_event(self):
        self.assertEqual(to_event_dict(self.events[2])["price_amount"], 0.0)

    def test_cancelled_online_and_undated(self):
        cancelled = {**self.events[0], "status": "canceled"}
        self.assertTrue(to_event_dict(cancelled)["is_cancelled"])
        self.assertIsNone(to_event_dict({**self.events[0], "online_event": True}))
        self.assertIsNone(to_event_dict({**self.events[0], "start": {}}))

    def test_event_venue(self):
        venue = event_venue(self.events[0])
        self.assertIn("Main Pub", venue["name"])
        self.assertAlmostEqual(venue["latitude"], 41.783, places=3)


class FindIdsTestCase(SimpleTestCase):
    def test_links_and_widgets(self):
        html = """
            <a href="https://www.eventbrite.com/e/7-below-tribute-to-phish-tickets-707179501927?aff=website">tix</a>
            <a href='https://www.eventbrite.com/e/1998894231455'>tix</a>
            <a href="https://www.eventbrite.com/o/the-main-pub-grille-taps-music-20010471604">us</a>
            <script>EBWidgets.createWidget({ widgetType: 'checkout', eventId: '2002225835372' })</script>
        """
        event_ids, organizer_ids = find_eventbrite_ids(html)
        self.assertEqual(event_ids, {"707179501927", "1998894231455", "2002225835372"})
        self.assertEqual(organizer_ids, {"20010471604"})

    def test_nothing_to_find(self):
        self.assertEqual(find_eventbrite_ids("<a href='https://dice.fm/event/x'>x</a>"), (set(), set()))
