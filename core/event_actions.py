"""
each event's row of link icons (calendar file, google calendar, map, share, save), made when
a page is rendered rather than stored with the event's html: so the icons can change without
re-rendering every stored event, and the save bookmark can show the visitor's own state from
their cookie, without javascript.

the stored html holds PLACEHOLDER where the row goes (core/templates/core/event.html); the
event_html template tag (core/templatetags/event_actions.py) fills it. the icons are symbols
defined once per page (core/templates/core/icons.html), so each row is a few <use> references.

a listing renders about a thousand rows, so they're plain strings, not reverse() and
format_html: those took 137ms a page on 2026-10-27, against about 20 for this. only the
event's own text is escaped; ids are integers, and the urls' shapes are fixed (core/urls.py).
"""

from django.utils.html import escape

from core.location import format_miles, miles
from django.utils.safestring import mark_safe

PLACEHOLDER = "<!--event-actions-->"


def icon(name):
    # a link's title is also its accessible name, as it has no text: no aria-label needed
    return f'<svg aria-hidden="true"><use href="#icon-{name}"></use></svg>'


ICAL, GCAL, MAP, SHARE, SAVE = (icon(name) for name in ("ical", "gcal", "map", "share", "save"))


def save_label(is_saved):
    return "Saved (click to remove)" if is_saved else "Save show"


def distance_html(event, location):
    """how far the event's venue is from the visitor's location, or "" without either"""
    venue = event.venue
    if location is None or venue is None or event.venue_override:
        return ""
    latitude, longitude = venue.exact_location
    if latitude is None or longitude is None:
        return ""
    return f'<span class="event-distance">({format_miles(miles(location.point, (latitude, longitude)))})</span>'


def actions_html(event, saved_ids, next_url, location=None):
    """
    the event's icon row, with the save bookmark filled when the visitor saved the show, and
    how far away it is when the visitor has given a location (core/location.py)
    """
    pk = int(event.pk)
    parts = [
        f'<div class="event-actions"><a href="/event/{pk}/ics" class="ical" title="Download to your calendar (.ics)">{ICAL}</a>',
        # /event/<id>/gcal redirects to google: building google's link for every event on
        # every page was slow (about 200ms a page in nyc noise)
        f'<a href="/event/{pk}/gcal" class="gcal" title="Add to Google Calendar">{GCAL}</a>',
    ]
    venue = event.venue
    if venue and not event.venue_override:
        maps_link = venue.google_maps_link
        if maps_link:
            parts.append(
                f'<a href="{escape(maps_link)}" class="map" title="Map: {escape(venue.name)}" target="_blank" rel="noopener">{MAP}</a>'
            )
    parts.append(
        f'<a href="/event/{pk}" class="share" data-event-title="{escape(event.title_and_artists)}" '
        f"onclick=\"return Share(this, '{pk}')\" title=\"Share\">{SHARE}</a>"
    )
    is_saved = pk in saved_ids
    # a form, so saving works without javascript; core/js/saved_shows.js saves in place
    parts.append(
        f'<form class="save-form" method="post" action="/saved/toggle/{pk}">'
        f'<input type="hidden" name="next" value="{escape(next_url)}#event-{pk}">'
        f'<button type="submit" class="save{" is-saved" if is_saved else ""}" data-event-id="{pk}" '
        f'aria-pressed="{"true" if is_saved else "false"}" title="{save_label(is_saved)}">{SAVE}</button></form>'
    )
    parts.append(f"{distance_html(event, location)}</div>")
    return mark_safe("".join(parts))


def with_actions(baked_html, event, saved_ids, next_url, location=None):
    return baked_html.replace(PLACEHOLDER, actions_html(event, saved_ids, next_url, location), 1)
