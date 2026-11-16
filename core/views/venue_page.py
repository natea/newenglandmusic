"""
a venue's own page at /venues/<slug> (add-venue-pages): the room's show bill. the name on the
plum tab, one line of facts (room, place, sub-region, map, what it books, open booking), then
every upcoming approved show night by night, then what musicians and fans need to know.

only new england's venues have pages, as only their shows are listed; a closed one (marked
inactive) answers 404. no map is drawn: the google places display terms aren't settled, so
the location is text and a link out to google maps.
"""

import datetime

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from core.artist_names import billing
from core.geo_filters import area_q, new_england_q
from core.models import Event, GeoArea, Venue
from core.opengraph import get_meta
from core.utils_datemath import beginning_of_day, get_current_new_york_datetime


def sub_region(venue):
    """the massachusetts sub-region the venue is in (each venue is in one), or None"""
    if venue.state.upper() != "MA":
        return None
    for area in GeoArea.objects.filter(kind=GeoArea.Kind.METRO).exclude(group=""):
        if Venue.objects.filter(pk=venue.pk).filter(area_q(area)).exists():
            return area
    return None


def nights(venue):
    """the bill: each upcoming approved show with its headliner and openers, in order"""
    today = beginning_of_day(get_current_new_york_datetime())
    shows = Event.objects.filter(venue=venue, starttime__gte=today).order_by("starttime", "same_time_order_override", "pk")
    tomorrow = today + datetime.timedelta(days=1)
    bill = []
    for event in shows:
        _, headliner, openers = billing(event)
        bill.append({"event": event, "headliner": headliner, "openers": openers, "tonight": event.starttime < tomorrow})
    return bill


def yes_no(value):
    """a yes-or-no fact, drawn only when it's known"""
    return {True: "Yes", False: "No"}.get(value, "")


def playing_here(venue):
    """[(label, value, url)] for musicians: only the fields the venue has"""
    fields = [
        ("Booking", venue.get_booking_type_display() if venue.booking_type and venue.booking_type != Venue.BookingType.UNKNOWN else "", ""),
        ("Open booking", yes_no(venue.open_booking), ""),
        ("Ask at", "Booking page" if venue.booking_url else "", venue.booking_url),
        ("Booking notes", venue.booking_notes, ""),
        ("Open mic", yes_no(venue.open_mic), ""),
        ("Books", venue.genre_notes, ""),
        ("Niche", venue.niche_notes, ""),
        ("Size", venue.get_size_display() if venue.size else "", ""),
    ]
    return [field for field in fields if field[1]]


def getting_here(venue):
    """[(label, value, url)] for fans: only the fields the venue has"""
    fields = [
        ("Where", venue.location, ""),
        ("Ages", venue.age_policy, ""),
        ("Access", venue.accessibility_notes, ""),
        ("Family-friendly", yes_no(venue.family_friendly), ""),
        ("LGBTQ+-friendly", yes_no(venue.lgbtq_friendly), ""),
        ("Website", venue.website.split("//", 1)[-1].rstrip("/") if venue.website else "", venue.website),
    ]
    return [field for field in fields if field[1]]


def venue_page(request, slug):
    venue = get_object_or_404(Venue.objects.filter(new_england_q()), slug=slug)
    # a venue marked inactive (closed, or not a music room) has no page; unknown status does
    if venue.is_active is False:
        raise Http404("no such venue")
    bill = nights(venue)
    area = sub_region(venue)
    place = ", ".join(bit for bit in (venue.neighborhood, venue.city_town, venue.state) if bit)
    playing = playing_here(venue)
    booking_link = (venue.booking_url or ("#playing-here" if playing else "")) if venue.open_booking else ""
    description = f"{venue.name}, {place}: upcoming shows" + (", and how to book it." if venue.open_booking else ".")
    return render(
        request,
        "core/venue.html",
        {
            "venue": venue,
            "room": " ".join(bit for bit in (venue.get_size_display().split(" (")[0] if venue.size else "", venue.venue_type.lower() if venue.size else venue.venue_type) if bit),
            "place": place,
            "area": area,
            # "MA: North of the Charles": the state is already in the line
            "area_label": area.label.split(": ", 1)[-1] if area else "",
            "booking_link": booking_link,
            "bill": bill,
            "playing_here": playing,
            "getting_here": getting_here(venue),
            "canonical": settings.SITE_URL.rstrip("/") + request.path,
            "meta": get_meta(title=f"{venue.name}, {venue.city_town or venue.state} | {settings.SITE_NAME}", description=description, url=request.build_absolute_uri()),
        },
    )
