"""
fetches venues and events from the seatgeek platform api (v2), for venues whose ticketing
pages (etix, axs and others) refuse our crawler. the api is free with a client id
(SEATGEEK_CLIENT_ID, from an app registered at seatgeek.com/account/develop), sent by
http basic auth so it's never in a url.

the api gives event details only: no ticket listings, no prices and no images. its links
go to seatgeek, which resells tickets, so they're stored but never shown (see fetch_events).
seatgeek publishes no rate limit.
"""

import datetime
import time

import requests
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.event_fetching.parsing import clean_description, clean_text, make_aware

BASE_URL = "https://api.seatgeek.com/2/"
USER_AGENT = "venue-db-event-check/1.0"
# no published limit, so the same gap as the eventbrite and apple music clients
MIN_SECONDS_BETWEEN_REQUESTS = 0.5
MAX_RETRIES = 2
TIMEOUT_SECONDS = 20
# a busy room like the sinclair lists over 50 shows (2026-10-29)
MAX_EVENTS_PER_VENUE = 100
# seatgeek's taxonomies for music; comedy, dance and the rest sit under "theater"
MUSIC_TAXONOMIES = {"concert", "music_festival"}


class SeatGeekError(Exception):
    pass


class SeatGeekClient:
    def __init__(self, client_id, session=None, sleep=time.sleep, clock=time.monotonic):
        self.client_id = client_id
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
        """the json response for an api path. errors name only the path and the failure"""
        for attempt in range(MAX_RETRIES + 1):
            self.throttle()
            try:
                response = self.session.get(
                    BASE_URL + path,
                    params=params,
                    auth=(self.client_id, ""),
                    headers={"User-Agent": USER_AGENT},
                    timeout=TIMEOUT_SECONDS,
                )
            except requests.RequestException as e:
                error = f"{path}: {type(e).__name__}"
            else:
                if response.status_code == 200:
                    return response.json()
                error = f"{path}: HTTP {response.status_code}"
                if response.status_code != 429 and response.status_code < 500:
                    raise SeatGeekError(error)
            if attempt < MAX_RETRIES:
                self.sleep(2**attempt)
        raise SeatGeekError(error)

    def venue_events(self, venue_id):
        """the venue's upcoming events, soonest first, as returned by the api"""
        data = self.get(
            "events",
            **{
                "venue.id": venue_id,
                "datetime_utc.gte": timezone.now().strftime("%Y-%m-%dT%H:%M:%S"),
            },
            sort="datetime_utc.asc",
            per_page=MAX_EVENTS_PER_VENUE,
        )
        return data.get("events", [])

    def search_venues(self, name, state):
        data = self.get("venues", q=name, state=state, per_page=20)
        return [to_venue_dict(venue) for venue in data.get("venues", [])]


def to_venue_dict(venue):
    location = venue.get("location") or {}
    return {
        "id": str(venue["id"]),
        "name": venue.get("name", ""),
        "address": venue.get("address") or "",
        "city": venue.get("city") or "",
        "state": venue.get("state") or "",
        "latitude": location.get("lat"),
        "longitude": location.get("lon"),
        "upcoming_events": int(venue.get("num_upcoming_events") or 0),
    }


def is_music(event):
    return any(t.get("name") in MUSIC_TAXONOMIES for t in event.get("taxonomies") or [])


def to_starttime(event):
    """returns (aware datetime, all_day), or (None, False) when the date isn't set"""
    if event.get("date_tbd") or event.get("datetime_tbd"):
        return None, False
    if event.get("time_tbd"):
        local = parse_datetime(event.get("datetime_local") or "")
        if local is None:
            return None, False
        return make_aware(datetime.datetime.combine(local.date(), datetime.time())), True
    utc = parse_datetime(event.get("datetime_utc") or "")
    if utc is None:
        return None, False
    return utc.replace(tzinfo=datetime.timezone.utc), False


def to_event_dict(event, ticket_url=""):
    """
    an event dict (see parsing.py), or None for events that aren't upcoming music.
    it links to `ticket_url`, the venue's own ticket page, never to seatgeek
    """
    if not is_music(event):
        return None
    starttime, all_day = to_starttime(event)
    if starttime is None:
        return None

    title = clean_text(event.get("title"))
    # the headliner is usually the title, e.g. "strongboi with Salami Rose Joe Louis"
    artists = [
        clean_text(p.get("name"))
        for p in event.get("performers") or []
        if p.get("name") and clean_text(p["name"]).lower() not in title.lower()
    ]
    return {
        "title": title,
        "artists": ", ".join(artists),
        "starttime": starttime,
        "all_day": all_day,
        "description": clean_description(event.get("description") or ""),
        "hyperlink": ticket_url,
        "ticket_hyperlink": ticket_url,
        # the api has no prices
        "price_amount": None,
        "is_cancelled": (event.get("status") or "").lower() in ("cancelled", "canceled"),
        "external_id": f"seatgeek:{event['id']}",
    }
