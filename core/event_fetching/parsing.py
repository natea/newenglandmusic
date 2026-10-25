"""
turns event data from venue websites (ical feeds, schema.org json-ld) into plain dicts
that the fetch_events command saves as Event rows.

every parser returns "event dicts" with these keys:
title, artists, starttime (aware datetime), all_day, description, hyperlink,
ticket_hyperlink, price_amount, is_cancelled, external_id
"""

import datetime
import hashlib
import html
import json
import re

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.html import strip_tags
from icalendar import Calendar

MAX_DESCRIPTION_LENGTH = 600

# calendar entries that mark the absence of an event, e.g. "No Event Tonight"
PLACEHOLDER_TITLE_RE = re.compile(r"^\s*(no (events?|shows?|music)\b|closed\b)", re.IGNORECASE)


def make_aware(value):
    """naive datetimes are taken to be in the venue's local time (settings.TIME_ZONE)"""
    if timezone.is_naive(value):
        return timezone.make_aware(value)
    return value


def to_starttime(value):
    """returns (aware datetime, all_day) from a date, datetime or iso string"""
    if isinstance(value, str):
        value = value.strip()
        parsed = parse_datetime(value)
        if parsed is None:
            parsed = parse_date(value[:10]) if len(value) >= 10 else None
        value = parsed
    if isinstance(value, datetime.datetime):
        return make_aware(value), False
    if isinstance(value, datetime.date):
        return make_aware(datetime.datetime.combine(value, datetime.time())), True
    return None, False


def clean_text(text):
    """plain text: html tags and entities (e.g. &#038;) removed, whitespace collapsed"""
    return " ".join(html.unescape(strip_tags(str(text or ""))).split())


def is_placeholder(title):
    return bool(PLACEHOLDER_TITLE_RE.match(title))


def clean_description(text):
    text = clean_text(text)
    if len(text) > MAX_DESCRIPTION_LENGTH:
        text = text[:MAX_DESCRIPTION_LENGTH].rsplit(" ", 1)[0] + "…"
    return text


def stable_id(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def parse_ical(body, source_url):
    events = []
    calendar = Calendar.from_ical(body)
    for component in calendar.walk("VEVENT"):
        starttime, all_day = to_starttime(component.decoded("DTSTART", None))
        if starttime is None:
            continue
        title = clean_text(component.get("SUMMARY", ""))
        if is_placeholder(title):
            continue
        # instances of a recurring event share a uid, so include the start time
        uid = stable_id(component.get("UID", "") or title, starttime.isoformat())
        events.append(
            {
                "title": title,
                "artists": "",
                "starttime": starttime,
                "all_day": all_day,
                "description": clean_description(str(component.get("DESCRIPTION", ""))),
                "hyperlink": str(component.get("URL", "")),
                "ticket_hyperlink": "",
                "price_amount": None,
                "is_cancelled": str(component.get("STATUS", "")).upper() == "CANCELLED",
                "external_id": f"ical:{uid}",
            }
        )
    return events


def iter_json_ld_nodes(scripts):
    """yields every dict node in a page's json-ld <script> blocks, including nested ones"""

    def walk(node):
        if isinstance(node, list):
            for item in node:
                yield from walk(item)
        elif isinstance(node, dict):
            yield node
            for value in node.values():
                yield from walk(value)

    for script in scripts:
        try:
            yield from walk(json.loads(script))
        except (json.JSONDecodeError, TypeError):
            continue


def is_event_node(node):
    types = node.get("@type", [])
    types = types if isinstance(types, list) else [types]
    return any(isinstance(t, str) and t.endswith("Event") for t in types)


def as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def first_price(offers):
    for offer in offers:
        if not isinstance(offer, dict):
            continue
        for key in ("price", "lowPrice"):
            try:
                return float(str(offer.get(key)).replace("$", "").replace(",", ""))
            except (TypeError, ValueError):
                continue
    return None


def parse_json_ld(scripts, page_url):
    events = []
    for node in iter_json_ld_nodes(scripts):
        if not is_event_node(node):
            continue
        starttime, all_day = to_starttime(node.get("startDate"))
        if starttime is None:
            continue
        title = clean_text(node.get("name", ""))
        if is_placeholder(title):
            continue
        url = node.get("url") if isinstance(node.get("url"), str) else ""
        offers = as_list(node.get("offers"))
        ticket_url = next(
            (o.get("url") for o in offers if isinstance(o, dict) and isinstance(o.get("url"), str)),
            "",
        )
        performers = [
            p.get("name") if isinstance(p, dict) else p
            for p in as_list(node.get("performer"))
        ]
        events.append(
            {
                "title": title,
                "artists": ", ".join(
                    clean_text(p) for p in performers if p and clean_text(p) != title
                ),
                "starttime": starttime,
                "all_day": all_day,
                "description": clean_description(node.get("description")),
                "hyperlink": url or page_url,
                "ticket_hyperlink": ticket_url,
                "price_amount": first_price(offers),
                "is_cancelled": "Cancelled" in str(node.get("eventStatus", "")),
                # recurring events often share one url, so include the start time
                "external_id": "json-ld:"
                + stable_id(url or page_url, title if not url else "", starttime.isoformat()),
            }
        )
    return events
