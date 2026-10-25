"""
fetches events and venues from the ticketmaster discovery api (v2), for venues that sell
tickets through ticketmaster -- its event pages block crawlers, but the api is open with
a free key (TICKETMASTER_API_KEY, the "consumer key" of an app on developer.ticketmaster.com).

api limits: 5 requests per second and 5000 per day.
"""

import datetime
import time

import requests
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time

from core.event_fetching.parsing import clean_description, clean_text, make_aware

BASE_URL = "https://app.ticketmaster.com/discovery/v2/"
# a little slower than the api's 5 requests per second
MIN_SECONDS_BETWEEN_REQUESTS = 0.25
MAX_RETRIES = 2
TIMEOUT_SECONDS = 20
# leaves out ticketmaster resale ("tmr"), which isn't the venue's own listing
EVENT_SOURCES = "ticketmaster,universe,frontgate"
MAX_EVENTS_PER_VENUE = 50


class TicketmasterError(Exception):
    pass


class TicketmasterClient:
    def __init__(self, api_key, session=None, sleep=time.sleep, clock=time.monotonic):
        self.api_key = api_key
        self.session = session or requests.Session()
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
        """the json response for an api path. errors never include the url, which has the key"""
        for attempt in range(MAX_RETRIES + 1):
            self.throttle()
            try:
                response = self.session.get(
                    BASE_URL + path,
                    params={"apikey": self.api_key, **params},
                    timeout=TIMEOUT_SECONDS,
                )
            except requests.RequestException as e:
                error = f"{path}: {type(e).__name__}"
            else:
                if response.status_code == 200:
                    return response.json()
                error = f"{path}: HTTP {response.status_code}"
                if response.status_code != 429 and response.status_code < 500:
                    raise TicketmasterError(error)
            if attempt < MAX_RETRIES:
                self.sleep(2**attempt)
        raise TicketmasterError(error)

    def venue_events(self, venue_id):
        """the venue's upcoming events, soonest first, as returned by the api"""
        data = self.get(
            "events.json",
            venueId=venue_id,
            startDateTime=timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            sort="date,asc",
            size=MAX_EVENTS_PER_VENUE,
            source=EVENT_SOURCES,
        )
        return data.get("_embedded", {}).get("events", [])

    def search_venues(self, keyword, state_code):
        data = self.get("venues.json", keyword=keyword, stateCode=state_code, size=20)
        return [to_venue_dict(venue) for venue in data.get("_embedded", {}).get("venues", [])]


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_venue_dict(venue):
    location = venue.get("location") or {}
    return {
        "id": venue["id"],
        "name": venue.get("name", ""),
        "address": (venue.get("address") or {}).get("line1", ""),
        "city": (venue.get("city") or {}).get("name", ""),
        "state": (venue.get("state") or {}).get("stateCode", ""),
        "latitude": to_float(location.get("latitude")),
        "longitude": to_float(location.get("longitude")),
    }


def primary_segment(event):
    classifications = event.get("classifications") or []
    primary = next((c for c in classifications if c.get("primary")), None)
    return ((primary or {}).get("segment") or {}).get("name", "")


def to_starttime(start):
    """returns (aware datetime, all_day), or (None, False) when the date isn't set"""
    date = parse_date(start.get("localDate") or "")
    if date is None or start.get("dateTBD") or start.get("dateTBA"):
        return None, False
    local_time = parse_time(start.get("localTime") or "")
    if start.get("timeTBA") or start.get("noSpecificTime") or local_time is None:
        return make_aware(datetime.datetime.combine(date, datetime.time())), True
    exact = parse_datetime(start.get("dateTime") or "")
    if exact is not None:
        return exact, False
    return make_aware(datetime.datetime.combine(date, local_time)), False


def to_event_dict(event):
    """an event dict (see parsing.py), or None for events that aren't upcoming music"""
    if event.get("test") or primary_segment(event) != "Music":
        return None
    starttime, all_day = to_starttime((event.get("dates") or {}).get("start") or {})
    if starttime is None:
        return None

    title = clean_text(event.get("name"))
    attractions = (event.get("_embedded") or {}).get("attractions") or []
    # the headliner is usually in the title, e.g. "Holywatr: Deo Gratias Tour"
    artists = [
        clean_text(a.get("name"))
        for a in attractions
        if a.get("name") and clean_text(a["name"]).lower() not in title.lower()
    ]
    prices = [p["min"] for p in event.get("priceRanges") or [] if p.get("min") is not None]
    status = ((event.get("dates") or {}).get("status") or {}).get("code", "")

    return {
        "title": title,
        "artists": ", ".join(artists),
        "starttime": starttime,
        "all_day": all_day,
        "description": clean_description(event.get("info") or event.get("pleaseNote") or ""),
        "hyperlink": event.get("url", ""),
        "ticket_hyperlink": event.get("url", ""),
        "price_amount": min(prices) if prices else None,
        "is_cancelled": status == "canceled",
        "external_id": f"tm:{event['id']}",
    }
