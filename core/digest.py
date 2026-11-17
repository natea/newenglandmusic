"""
which shows a subscriber's choices select, for the weekly email (add-weekly-email-digest).

    window = send_window(date(2026, 11, 5))
    venues = located_venues()                # once per run, for the "near a place" choices
    events_for(subscriber, window, venues)   # approved, uncancelled events, once each

a show is selected when any one choice matches it: an area (by the listing's geo-filter rules),
a followed town or venue, or a venue within some miles of a stored point.
"""

import datetime
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.http import QueryDict

from core import location
from core.geo_filters import new_england_q, parse_geo_filter
from core.models import DigestChoice, Event, Venue

NEW_YORK = ZoneInfo("America/New_York")
ALL_AREAS = "all=1"
MAX_CHOICES = 20
WINDOW_DAYS = 8  # the send day and the seven days after it


def send_window(send_day):
    """(start, end) aware datetimes: the start of send_day to the end of the seventh day after"""
    start = datetime.datetime.combine(send_day, datetime.time.min, tzinfo=NEW_YORK)
    end = datetime.datetime.combine(send_day + datetime.timedelta(days=WINDOW_DAYS), datetime.time.min, tzinfo=NEW_YORK)
    return start, end


def week_of(day):
    """the monday on or before day"""
    return day - datetime.timedelta(days=day.weekday())


def located_venues():
    """[(venue id, (latitude, longitude))] for venues with coordinates"""
    found = []
    for venue in Venue.objects.only(
        "id", "latitude", "longitude", "place_latitude", "place_longitude", "place_lookup_status"
    ):
        point = venue.exact_location
        if None not in point:
            found.append((venue.pk, point))
    return found


def area_filter(choice):
    """the GeoFilter an area choice stores, or None when it no longer holds in whole"""
    geo_filter = parse_geo_filter(QueryDict(choice.area_query), new_england_only=True)
    # an unknown slug is dropped by the parse, which would widen the choice, so a choice
    # that doesn't parse back to exactly what was stored is stale
    if not geo_filter or geo_filter.query_string != choice.area_query:
        return None
    return geo_filter


def is_stale(choice):
    """an area choice that names something gone, in whole or in part"""
    return choice.kind == DigestChoice.Kind.AREA and choice.area_query != ALL_AREAS and area_filter(choice) is None


def choice_q(choice, venues):
    """the Q on Event one choice selects, or None when it selects nothing"""
    kind = DigestChoice.Kind
    if choice.kind == kind.AREA:
        if choice.area_query == ALL_AREAS:
            return Q(venue__isnull=False)
        geo_filter = area_filter(choice)
        return geo_filter.q(prefix="venue__") if geo_filter else None
    if choice.kind == kind.TOWN:
        return Q(venue__city_town__iexact=choice.town, venue__state=choice.state)
    if choice.kind == kind.VENUE:
        return Q(venue_id=choice.venue_id) if choice.venue_id else None
    if choice.kind == kind.NEAR and None not in (choice.latitude, choice.longitude, choice.miles):
        point = (choice.latitude, choice.longitude)
        ids = [pk for pk, there in venues if location.miles(point, there) <= choice.miles]
        return Q(venue_id__in=ids) if ids else None
    return None


def events_for(subscriber, window, venues=None):
    """the subscriber's selected events starting in window, in start order, each once"""
    choices = list(subscriber.choices.all())
    if venues is None and any(choice.kind == DigestChoice.Kind.NEAR for choice in choices):
        venues = located_venues()
    selected = Q()
    for choice in choices:
        q = choice_q(choice, venues or [])
        if q is not None:
            selected |= q
    if not selected:
        return Event.objects.none()
    start, end = window
    # a null start time never passes the range; like the listings, only new england's shows
    return (
        Event.objects.filter(selected, starttime__gte=start, starttime__lt=end, is_cancelled=False)
        .filter(new_england_q("venue__"))
        .select_related("venue")
        .order_by("starttime", "pk")
    )


# the weekly email

MAX_SHOWN = 50
SUBJECT = "Your weekly shows"


def one_line(text):
    return " ".join((text or "").split())


def format_time(moment):
    local = moment.astimezone(NEW_YORK)
    hour = local.hour % 12 or 12
    suffix = "pm" if local.hour >= 12 else "am"
    return f"{hour}{suffix}" if local.minute == 0 else f"{hour}:{local.minute:02d}{suffix}"


def see_all_query(subscriber):
    """the listing's filter for the first area choice that still holds, or "" for the whole listing"""
    for choice in subscriber.choices.filter(kind=DigestChoice.Kind.AREA):
        if choice.area_query != ALL_AREAS and area_filter(choice):
            return choice.area_query
    return ""


def build_weekly(subscriber, events, site_url):
    """
    (subject, text, html, headers) for the subscriber's selected events, at most MAX_SHOWN of them
    in start order, by date. site_url turns a path into the site's own address: events link to
    their page here, never to the event's source
    """
    from django.template.loader import render_to_string
    from django.urls import reverse

    from core import digest_tokens

    events = list(events)
    days = []
    for event in events[:MAX_SHOWN]:
        local = event.starttime.astimezone(NEW_YORK)
        if not days or days[-1]["date"] != local.date():
            days.append({"date": local.date(), "label": f"{local:%a %b} {local.day}", "events": []})
        venue = event.venue
        days[-1]["events"].append(
            {
                "title": one_line(event.title) or one_line(event.artists) or "Untitled show",
                "artists": one_line(event.artists) if event.title else "",
                "venue": one_line(venue.name) if venue else "",
                "town": one_line(venue.city_town) if venue else "",
                "time": format_time(event.starttime),
                "url": site_url(reverse("event_page", args=[event.pk])),
            }
        )
    unsubscribe = site_url(reverse("digest_unsubscribe", args=[digest_tokens.unsubscribe_token(subscriber)]))
    query = see_all_query(subscriber)
    context = {
        "days": days,
        "total": len(events),
        "see_all": site_url("/" + (f"?{query}" if query else "")) if len(events) > MAX_SHOWN else "",
        "unsubscribe": unsubscribe,
        "sign_in": site_url(reverse("digest_sign_in")),
    }
    text = render_to_string("core/email/weekly_digest.txt", context)
    html = render_to_string("core/email/weekly_digest.html", context)
    headers = {"List-Unsubscribe": f"<{unsubscribe}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}
    return SUBJECT, text, html, headers
