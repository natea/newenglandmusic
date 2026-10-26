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
from urllib.parse import urlparse

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.html import strip_tags
from icalendar import Calendar

MAX_DESCRIPTION_LENGTH = 600

# calendar entries that mark the absence of an event, e.g. "No Event Tonight"
PLACEHOLDER_TITLE_RE = re.compile(r"^\s*(no (events?|shows?|music)\b|closed\b)", re.IGNORECASE)
# the wordpress events calendar puts every timezone in one VTIMEZONE block, which the
# icalendar library can't read; each TZID line starts a timezone of its own
VTIMEZONE_RE = re.compile(r"BEGIN:VTIMEZONE\r?\n(.*?)END:VTIMEZONE", re.DOTALL)
TZID_LINE_RE = re.compile(r"^TZID:", re.MULTILINE)
BLOCK_TAG_RE = re.compile(r"</?(p|div|h[1-6]|br|li|tr|td)\b", re.IGNORECASE)
# the json data blocks a react-on-rails page (e.g. opendate's) hands to its components
REACT_ON_RAILS_DATA_RE = re.compile(
    r"<script[^>]*\bjs-react-on-rails-component\b[^>]*>(.*?)</script>", re.DOTALL
)


def make_aware(value):
    """naive datetimes are taken to be in the venue's local time (settings.TIME_ZONE)"""
    if timezone.is_naive(value):
        return timezone.make_aware(value)
    return value


def to_starttime(value):
    """returns (aware datetime, all_day) from a date, datetime or iso string"""
    if isinstance(value, str):
        value = value.strip()
        # parse_datetime reads a bare date as midnight, so check for one first
        parsed = parse_date(value) if len(value) == 10 else parse_datetime(value)
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
    # some feeds escape their html (&lt;p&gt;), so unescape before stripping tags too
    text = html.unescape(str(text or ""))
    # block tags separate words, so "<h2>Show</h2><p>Doors" doesn't become "ShowDoors"
    text = BLOCK_TAG_RE.sub(r" \g<0>", text)
    return " ".join(html.unescape(strip_tags(text)).split())


def is_placeholder(title):
    return bool(PLACEHOLDER_TITLE_RE.match(title))


def clean_description(text):
    text = clean_text(text)
    if len(text) > MAX_DESCRIPTION_LENGTH:
        text = text[:MAX_DESCRIPTION_LENGTH].rsplit(" ", 1)[0] + "…"
    return text


def stable_id(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def is_opendate_url(url):
    host = urlparse(url or "").netloc.lower()
    return host == "opendate.io" or host.endswith(".opendate.io")


def is_opendate_event_url(url):
    return is_opendate_url(url) and urlparse(url).path.startswith("/e/")


def is_placeholder_midnight(event):
    """a start that stands in for "no time": midnight eastern, either local (00:00) or
    standard time (05:00 utc, which shows as 1am in summer), on an event whose ticket link
    is an opendate event page -- e.g. a venue site listing opendate's date-only events"""
    if event["all_day"] or not is_opendate_event_url(event["ticket_hyperlink"]):
        return False
    local = timezone.localtime(event["starttime"]).time()
    utc = event["starttime"].astimezone(datetime.timezone.utc).time()
    return local == datetime.time(0, 0) or utc == datetime.time(5, 0)

def opendate_start_time(page_html):
    """the start time on an opendate event page, or None. its json-ld gives only the date,
    but the data its "add to calendar" button reads has the full time and utc offset"""
    for block in REACT_ON_RAILS_DATA_RE.findall(page_html or ""):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        confirm = data.get("confirm") if isinstance(data, dict) else None
        start = confirm.get("start_time") if isinstance(confirm, dict) else None
        try:
            parsed = parse_datetime(start) if isinstance(start, str) else None
        except ValueError:
            parsed = None
        if parsed:
            return make_aware(parsed)
    return None

def with_opendate_time(event, page_html):
    """the event at its opendate page's start time when that's on the event's date;
    otherwise the event as all-day ("time TBA"). the event's external_id is left as it
    was, so filling in the time updates the saved event rather than adding another."""
    start = opendate_start_time(page_html)
    if start and timezone.localdate(start) == timezone.localdate(event["starttime"]):
        return {**event, "starttime": start, "all_day": False}
    return {**event, "all_day": True}

def split_merged_timezones(text):
    """one VTIMEZONE block per TZID, for feeds that merge several into one"""

    def split(match):
        inner = match.group(1)
        starts = [line.start() for line in TZID_LINE_RE.finditer(inner)]
        if len(starts) < 2:
            return match.group(0)
        newline = "\r\n" if "\r\n" in match.group(0) else "\n"
        parts = [inner[a:b] for a, b in zip(starts, starts[1:] + [len(inner)])]
        return newline.join(f"BEGIN:VTIMEZONE{newline}{part}END:VTIMEZONE" for part in parts)

    return VTIMEZONE_RE.sub(split, text)


def parse_ical(body, source_url):
    events = []
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    calendar = Calendar.from_ical(split_merged_timezones(body))
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
