"""
an event's own page at /event/<id> (add-event-pages): an index card like the band pages, with
the date on the tab, the headliner and openers linked to their pages, the venue's facts, the
ticket and venue links, the description and the play buttons. it used to redirect into the
month's listing; the share preview's title and description are the same as before.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.template.defaultfilters import date as django_date_format

from core.artist_previews import event_artist_previews
from core.event_actions import actions_html
from core.event_performers import linked_billing
from core.geo_filters import NEW_ENGLAND_STATES
from core.location import location_from_request
from core.models import Event
from core.opengraph import get_meta
from core.saved_shows import COOKIE_NAME, parse_saved
from core.utils_datemath import NYCTZ, beginning_of_day, get_current_new_york_datetime


def share_title(event):
    """"7pm @ Paradise - Belly: Anjimile", the title shared links have always previewed"""
    venue = event.venue_override if event.venue_override else event.venue
    # django's "f" format: the 12-hour time with zero minutes left off ("7pm", not "7:00pm")
    when = event.starttime_override or django_date_format(event.starttime.astimezone(NYCTZ), "n/j fA").lower()
    return f"{when} @ {venue} - {event.title_and_artists or ''}"


def same_link(first, second):
    """
    whether two links go to the same page: equal once trimmed, with the scheme and host
    lowercased, a trailing slash dropped, and utm_ tracking taken out of the query
    """

    def normal(url):
        parts = urlsplit(url.strip())
        query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith("utm_")])
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, parts.fragment))

    return normal(first) == normal(second)


def outbound_links(event):
    """[(label, url)]: "Tickets" and "Venue's page", or one "Tickets" when they're the same"""
    tickets, page = (event.ticket_hyperlink or "").strip(), (event.hyperlink or "").strip()
    if tickets and page and same_link(tickets, page):
        return [("Tickets", tickets)]
    return [(label, url) for label, url in (("Tickets", tickets), ("Venue's page", page)) if url]


def venue_page_url(venue):
    """the venue's page, when it has one: an active-or-unknown new england venue (add-venue-pages)"""
    if venue is None or not venue.slug or venue.is_active is False or venue.state.upper() not in NEW_ENGLAND_STATES:
        return ""
    return venue.get_absolute_url()


def event_page(request, event_id):
    # Event.objects holds approved events only, so an unapproved one is a 404
    event = get_object_or_404(Event.objects.select_related("venue"), pk=event_id)
    title_line, headliner, openers = linked_billing(event)
    saved = set(parse_saved(request.COOKIES.get(COOKIE_NAME)))
    # a show is past from the day after it, in new york: tonight's is still on
    is_past = event.starttime < beginning_of_day(get_current_new_york_datetime())
    venue = event.venue
    description = " · ".join(
        bit for bit in (
            event.title_and_artists,
            django_date_format(event.starttime.astimezone(NYCTZ), "l, F j"),
            str(event.venue_override or venue or ""),
        ) if bit
    )
    return render(
        request,
        "core/event_page.html",
        {
            "event": event,
            "venue": venue,
            "venue_url": venue_page_url(venue),
            "title_line": title_line,
            "headliner": headliner,
            "openers": openers,
            "actions": actions_html(event, saved, request.path, location_from_request(request)),
            "links": outbound_links(event),
            "artist_previews": event_artist_previews(event),
            "is_past": is_past,
            "canonical": settings.SITE_URL.rstrip("/") + request.path,
            "meta": get_meta(title=share_title(event), description=description, url=request.build_absolute_uri()),
        },
    )
