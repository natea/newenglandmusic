"""
events as icalendar, for the single-event ICAL download and the area feeds at
/calendar.ics?region=…&state=…&metro=… (core/views/calendar_feed.py).

an event's UID is the same in every feed and download, so calendar apps that refresh a
subscribed feed update their copy of an event rather than adding another. nothing in an
event's entry depends on when it's built (DTSTAMP is when the event was created), so an
unchanged feed is byte for byte the same, and its ETag matches.
"""

import datetime
from urllib.parse import quote, urlparse

from django.conf import settings
from django.urls import reverse
from django.utils.html import strip_tags
from icalendar import Calendar
from icalendar import Event as ICalEvent
from icalendar import vDuration

REFRESH = datetime.timedelta(hours=6)


def event_uid(event):
    # settings.UID_DOMAIN, not the site's host: a move to a custom domain mustn't change
    # every event's UID, or each subscriber's calendar would show every show twice
    return f"event-{event.pk}@{settings.UID_DOMAIN}"


def event_to_ical(event):
    entry = ICalEvent()
    entry.add("UID", event_uid(event))
    entry.add("DTSTAMP", event.created_at)
    entry.add("DTSTART", event.starttime)
    entry.add("DTEND", event.starttime + datetime.timedelta(hours=1))
    entry.add("SUMMARY", event.calendar_name)
    entry.add("LOCATION", event.venue_name_and_address)
    entry.add("DESCRIPTION", strip_tags(event.description or ""))
    entry.add("URL", settings.SITE_URL.rstrip("/") + reverse("event_redirect", args=[event.pk]))
    if event.is_cancelled:
        entry.add("STATUS", "CANCELLED")
    return entry


def calendar(events, area_label=""):
    """a calendar of these events, named for the area when there is one"""
    cal = Calendar()
    site_name = settings.SITE_NAME
    cal.add("PRODID", f"-//{site_name}//{urlparse(settings.SITE_URL).netloc}//EN")
    cal.add("VERSION", "2.0")
    cal.add("CALSCALE", "GREGORIAN")
    cal.add("METHOD", "PUBLISH")
    cal.add("X-WR-CALNAME", f"{site_name}: {area_label}" if area_label else site_name)
    cal.add("X-WR-CALDESC", f"Live music from {site_name}, {settings.SITE_URL}")
    cal.add("X-WR-TIMEZONE", "America/New_York")
    # typed, or icalendar writes these unknown properties as text ("6:00:00", not "PT6H")
    cal.add("REFRESH-INTERVAL", vDuration(REFRESH), parameters={"VALUE": "DURATION"})
    cal.add("X-PUBLISHED-TTL", vDuration(REFRESH))
    for event in events:
        cal.add_component(event_to_ical(event))
    return cal.to_ical()


def subscribe_links(geo_filter):
    """the area's feed: its https url, its webcal:// url for calendar apps, and google's"""
    query = f"?{geo_filter.query_string}" if geo_filter else ""
    url = settings.SITE_URL.rstrip("/") + reverse("calendar_feed") + query
    webcal = "webcal://" + url.split("://", 1)[-1]
    return {
        "url": url,
        "webcal": webcal,
        "google": "https://calendar.google.com/calendar/r?cid=" + quote(webcal, safe=""),
    }
