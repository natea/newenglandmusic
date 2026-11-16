"""
a venue's artist view at /venues/<slug>/booking (add-venue-list): beside its fan page, what a
band needs to ask for a show there, from what the venue record already holds. whether it
takes open bookings, what kind of booking it does in plain words, how to apply, its notes,
open mic, size and genres. kept out of search engines: it's a thin page beside the fan page.
"""

from django.conf import settings
from django.shortcuts import render

from core.models import Venue
from core.opengraph import get_meta
from core.views.venue_page import venue_with_a_page, yes_no

# the sheet's booking types are its editors' shorthand; each gets a line a stranger can read
# (wording approved by the owner, 2026-11-16). "unknown" is never shown
BOOKING_MEANINGS = {
    Venue.BookingType.SUBMIT_ARTIST: "Send them your act and they'll place you on a bill.",
    Venue.BookingType.SUBMIT_SHOW: "Pitch a complete show (the whole bill) and they host it.",
    Venue.BookingType.LOCALS_ONLY: "Books local acts only.",
    Venue.BookingType.DART_THROW: "No set process; reach out and see.",
    Venue.BookingType.TOURING_ONLY: "Books touring acts only.",
    Venue.BookingType.MUST_INCLUDE_LOCAL: "A touring bill must include a local act.",
}


def open_booking_statement(venue):
    return {True: "Takes open bookings", False: "Doesn't take open bookings"}.get(venue.open_booking, "Not known")


def booking_type(venue):
    """(label, meaning) for a known booking type, or None"""
    if not venue.booking_type or venue.booking_type == Venue.BookingType.UNKNOWN:
        return None
    return venue.get_booking_type_display(), BOOKING_MEANINGS.get(venue.booking_type, "")


def how_to_apply(venue):
    """(label, url): the booking link, or else the venue's website; None without either"""
    if venue.booking_url:
        return "Booking page", venue.booking_url
    if venue.website:
        return venue.website.split("//", 1)[-1].rstrip("/"), venue.website
    return None


def venue_booking(request, slug):
    venue = venue_with_a_page(slug)
    kind = booking_type(venue)
    apply = how_to_apply(venue)
    fields = [
        (label, value) for label, value in (
            ("Open mic", yes_no(venue.open_mic)),
            ("Size", venue.get_size_display() if venue.size else ""),
            ("Books", ", ".join(g for g in venue.genres if g.upper() != "ALL") or ("Any genre" if venue.genres else "")),
            ("Genre notes", venue.genre_notes),
            ("Niche", venue.niche_notes),
        ) if value
    ]
    # nothing about booking at all: say so, and point at the website when there is one
    known = venue.open_booking is not None or kind or venue.booking_url or venue.booking_notes or fields
    return render(
        request,
        "core/venue_booking.html",
        {
            "venue": venue,
            "tab": "artists",
            "statement": open_booking_statement(venue),
            "booking_type": kind,
            "apply": apply,
            "fields": fields,
            "known": known,
            "meta": get_meta(
                title=f"Booking {venue.name}, {venue.city_town or venue.state} | {settings.SITE_NAME}",
                description=f"How to book a show at {venue.name}: whether it takes open bookings, how to apply, and what it books.",
                url=request.build_absolute_uri(),
            ),
        },
    )
