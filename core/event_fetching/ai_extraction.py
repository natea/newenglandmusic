"""
extracts events from a venue web page's text with claude, for venues whose sites have
no ical feed or structured event data.
"""

import datetime
import json

import anthropic
from django.utils import timezone

from core.event_fetching.parsing import (
    clean_description,
    clean_text,
    is_placeholder,
    make_aware,
    stable_id,
)

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """\
You extract upcoming events from the text of a music venue's web page, for a calendar \
of live music in the northeastern US.

The page text comes from the venue's website. Link targets appear in angle brackets \
after the link text. List every distinct upcoming event the page shows as taking place \
at this venue. Leave out past events, events at other venues, recurring business hours, \
and promotions that are not events.

For each event:
- title: the event or headliner name, as written on the page.
- artists: other performers or support acts, comma-separated; empty if none are listed.
- start_date: YYYY-MM-DD. When the page leaves out the year, use the first date on or \
after today's date that matches.
- start_time: HH:MM in 24-hour time, local to the venue; prefer the show time over the \
doors time; empty if the page gives no time.
- url: the link to the event's own page, if there is one; otherwise empty.
- ticket_url: the link to buy tickets, if there is one; otherwise empty.
- price: the price as written (e.g. "$15", "Free", "$20 adv / $25 door"); empty if not given.
- description: one or two sentences from the page about the event; empty if there is none.

Use only what the page says. When a field isn't on the page, leave it empty rather than \
guessing. If the page lists no upcoming events, return an empty list."""

EVENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "artists": {"type": "string"},
                    "start_date": {"type": "string"},
                    "start_time": {"type": "string"},
                    "url": {"type": "string"},
                    "ticket_url": {"type": "string"},
                    "price": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": [
                    "title",
                    "artists",
                    "start_date",
                    "start_time",
                    "url",
                    "ticket_url",
                    "price",
                    "description",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["events"],
    "additionalProperties": False,
}


class ExtractionError(Exception):
    pass


def parse_price(price_text):
    price_text = price_text.strip().lower()
    if not price_text:
        return None
    if price_text.startswith("free"):
        return 0.0
    digits = "".join(c if c.isdigit() or c == "." else " " for c in price_text).split()
    try:
        return float(digits[0]) if digits else None
    except ValueError:
        return None


def to_event_dict(raw, page_url):
    if is_placeholder(raw["title"]):
        return None
    try:
        date = datetime.date.fromisoformat(raw["start_date"])
    except ValueError:
        return None
    all_day = True
    time = datetime.time()
    if raw["start_time"]:
        try:
            time = datetime.time.fromisoformat(raw["start_time"])
            all_day = False
        except ValueError:
            pass
    starttime = make_aware(datetime.datetime.combine(date, time))
    return {
        "title": clean_text(raw["title"]),
        "artists": clean_text(raw["artists"]),
        "starttime": starttime,
        "all_day": all_day,
        "description": clean_description(raw["description"]),
        "hyperlink": raw["url"] or page_url,
        "ticket_hyperlink": raw["ticket_url"],
        "price_amount": parse_price(raw["price"]),
        "is_cancelled": False,
        # recurring events often share one url, so include the start time
        "external_id": "ai:"
        + stable_id(raw["url"] or page_url, raw["title"] if not raw["url"] else "", starttime.isoformat()),
    }


def extract_events(client, venue_name, venue_location, page_url, page_text):
    today = timezone.localdate().isoformat()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        # if the model declines a request, the api re-runs it on a fallback model
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": EVENTS_SCHEMA},
        },
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Venue: {venue_name} ({venue_location})\n"
                    f"Today's date: {today}\n"
                    f"Page: {page_url}\n\n"
                    f"<page_text>\n{page_text}\n</page_text>"
                ),
            }
        ],
    )
    if response.stop_reason != "end_turn":
        raise ExtractionError(f"stopped with {response.stop_reason}")
    text = next(block.text for block in response.content if block.type == "text")
    raw_events = json.loads(text)["events"]
    events = [to_event_dict(raw, page_url) for raw in raw_events]
    return [event for event in events if event], response.usage
