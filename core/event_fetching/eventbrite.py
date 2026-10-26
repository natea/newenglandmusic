"""
fetches events from the eventbrite api (v3), for venues that sell tickets through their
own eventbrite organizer account -- eventbrite's pages are slow and unreliable to crawl,
but the api is open with a private token (EVENTBRITE_API_KEY, from the account's
eventbrite.com/platform/api-keys page).

eventbrite has no public event search, so events are reached through ids: a venue's
pages link its events (eventbrite.com/e/...-<event id>) or its organizer page
(eventbrite.com/o/...-<organizer id>), and an event's details name its organizer.
"""

import re
import time

import requests
from django.utils.dateparse import parse_datetime

from core.event_fetching.parsing import clean_description, clean_text

BASE_URL = "https://www.eventbriteapi.com/v3/"
# eventbrite allows 2000 requests an hour per token; this stays well under it
MIN_SECONDS_BETWEEN_REQUESTS = 0.5
MAX_RETRIES = 2
TIMEOUT_SECONDS = 20
MAX_PAGES = 5

# links and widgets on a venue's own pages. event ids are long; organizer ids a little shorter
EVENT_ID_RES = (
    re.compile(r"eventbrite\.[a-z.]+/e/(?:[^\s\"'<>/?#]*-)?(\d{9,})"),
    # the embedded checkout widget: EBWidgets.createWidget({ eventId: '123...' })
    re.compile(r"eventId['\"]?\s*:\s*['\"]?(\d{9,})"),
)
ORGANIZER_ID_RE = re.compile(r"eventbrite\.[a-z.]+/o/(?:[^\s\"'<>/?#]*-)?(\d{6,})")


class EventbriteError(Exception):
    pass


def find_eventbrite_ids(html):
    """(event ids, organizer ids) linked from a page's html"""
    event_ids = {match for regex in EVENT_ID_RES for match in regex.findall(html)}
    return event_ids, set(ORGANIZER_ID_RE.findall(html))


class EventbriteClient:
    def __init__(self, api_key, session=None, sleep=time.sleep, clock=time.monotonic):
        self.session = session or requests.Session()
        # the token goes in a header, so it never appears in a url or an error
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.sleep = sleep
        self.clock = clock
        self.last_request_at = None

    def throttle(self):
        if self.last_request_at is not None:
            wait = self.last_request_at + MIN_SECONDS_BETWEEN_REQUESTS - self.clock()
            if wait > 0:
                self.sleep(wait)
        self.last_request_at = self.clock()

    def get(self, path, **params):
        for attempt in range(MAX_RETRIES + 1):
            self.throttle()
            try:
                response = self.session.get(
                    BASE_URL + path, params=params, headers=self.headers, timeout=TIMEOUT_SECONDS
                )
            except requests.RequestException as e:
                error = f"{path}: {type(e).__name__}"
            else:
                if response.status_code == 200:
                    return response.json()
                error = f"{path}: HTTP {response.status_code}"
                if response.status_code != 429 and response.status_code < 500:
                    raise EventbriteError(error)
            if attempt < MAX_RETRIES:
                self.sleep(2**attempt)
        raise EventbriteError(error)

    def event(self, event_id):
        return self.get(f"events/{event_id}/")

    def organizer_events(self, organizer_id):
        """the organizer's live events, soonest first, with their venues and ticket prices"""
        events, continuation = [], None
        for _ in range(MAX_PAGES):
            params = {
                "status": "live",
                "order_by": "start_asc",
                "expand": "venue,ticket_availability",
            }
            if continuation:
                params["continuation"] = continuation
            data = self.get(f"organizers/{organizer_id}/events/", **params)
            events += data.get("events", [])
            pagination = data.get("pagination") or {}
            continuation = pagination.get("continuation")
            if not pagination.get("has_more_items") or not continuation:
                break
        return events


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def event_venue(event):
    """where an event is: its venue's name and coordinates, for matching it to ours"""
    venue = event.get("venue") or {}
    return {
        "name": venue.get("name") or "",
        "latitude": to_float(venue.get("latitude")),
        "longitude": to_float(venue.get("longitude")),
    }


def price_amount(event):
    if event.get("is_free"):
        return 0.0
    minimum = (event.get("ticket_availability") or {}).get("minimum_ticket_price") or {}
    return to_float(minimum.get("major_value"))


def to_event_dict(event):
    """an event dict (see parsing.py), or None for online or undated events"""
    if event.get("online_event"):
        return None
    starttime = parse_datetime(((event.get("start") or {}).get("utc")) or "")
    if starttime is None:
        return None
    url = event.get("url", "")
    return {
        "title": clean_text((event.get("name") or {}).get("text")),
        "artists": "",
        "starttime": starttime,
        "all_day": False,
        "description": clean_description(
            (event.get("description") or {}).get("text") or event.get("summary") or ""
        ),
        "hyperlink": url,
        "ticket_hyperlink": url,
        "price_amount": price_amount(event),
        "is_cancelled": event.get("status") == "canceled",
        "external_id": f"eventbrite:{event['id']}",
    }
