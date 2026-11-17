"""
the list of venues at /venues (add-venue-list): every venue that isn't marked inactive, A to
Z ("The" ignored), each with its town, kind and size of room and genres. it narrows by place
as the homepage's events do (the same parameters and remembered cookie), by genre, and, for
artists, to the venues that take open bookings, whose entries then link to their artist
views. genre and open booking are only ever in the address, never remembered.
"""

from collections import Counter, defaultdict
from urllib.parse import parse_qsl, urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render

from core.geo_filters import CookieAction, apply_cookie_action, geo_filter_context, geo_filter_for_request, new_england_q
from core.models import Venue
from core.opengraph import get_meta
from core.views.act_index import LETTERS, letter_of, sort_name


def genre_choices(venues):
    """
    the genres the venues list, one per spelling ignoring case, sorted, without "ALL": shown in
    the spelling most venues use, a capitalised one on a tie ("Jazz" over "jazz")
    """
    spellings = defaultdict(Counter)
    for venue in venues:
        for genre in venue.genres:
            key = genre.strip().casefold()
            if key and key != "all":
                spellings[key][genre.strip()] += 1
    shown = [max(counts, key=lambda s: (counts[s], s[:1].isupper(), s)) for counts in spellings.values()]
    return sorted(shown, key=str.casefold)


def books_genre(venue, genre):
    """a venue books a genre when it lists it, or lists "ALL", ignoring case"""
    listed = {g.strip().casefold() for g in venue.genres}
    return "all" in listed or genre.casefold() in listed


def extras_of(genre, open_booking):
    """the list's own parameters, which the place form and its redirect carry along"""
    return [(name, value) for name, value in (("genre", genre), ("open_booking", "1" if open_booking else "")) if value]


def venue_list(request):
    geo_filter, cookie_action = geo_filter_for_request(request)
    every = list(Venue.objects.filter(new_england_q()).exclude(is_active=False).exclude(slug=None))
    genres = genre_choices(every)
    asked = request.GET.get("genre", "").strip()
    # an unknown genre is ignored, as an unknown area is
    genre = next((g for g in genres if g.casefold() == asked.casefold()), "")
    open_booking = request.GET.get("open_booking") == "1"
    extras = extras_of(genre, open_booking)
    if cookie_action == CookieAction.REDIRECT:
        # the remembered place, in the address, keeping the list's own filters
        return HttpResponseRedirect(f"{request.path}?{geo_filter.query_string}" + (f"&{urlencode(extras)}" if extras else ""))

    venues = Venue.objects.filter(new_england_q()).exclude(is_active=False).exclude(slug=None)
    if geo_filter:
        venues = venues.filter(geo_filter.q())
    if open_booking:
        venues = venues.filter(open_booking=True)
    venues = [v for v in venues if not genre or books_genre(v, genre)]
    venues.sort(key=lambda v: sort_name(v.name).casefold())

    groups = {letter: [] for letter in LETTERS}
    for venue in venues:
        venue.room = " · ".join(bit for bit in (venue.venue_type, venue.get_size_display().split(" (")[0] if venue.size else "") if bit)
        named = [g for g in venue.genres if g.strip().casefold() != "all"]
        venue.genre_line = ", ".join(named) if named else ("Any genre" if venue.genres else "")
        venue.booking_label = venue.get_booking_type_display() if venue.booking_type and venue.booking_type != Venue.BookingType.UNKNOWN else ""
        groups[letter_of(venue.name)].append(venue)

    filtered = bool(geo_filter) or bool(genre) or open_booking
    response = render(
        request,
        "core/venue_list.html",
        {
            **geo_filter_context(geo_filter),
            "form_extras": extras,
            "groups": [(letter, entries) for letter, entries in groups.items() if entries],
            "rail": [(letter, bool(entries)) for letter, entries in groups.items()],
            "count": len(venues),
            "genres": genres,
            "genre": genre,
            "open_booking": open_booking,
            # the place, for the genre and artists forms to carry along
            "place_params": parse_qsl(geo_filter.query_string) if geo_filter else [],
            "no_match": filtered and not venues,
            "canonical": settings.SITE_URL.rstrip("/") + "/venues",
            "meta": get_meta(
                url="/venues", title=f"Venues | {settings.SITE_NAME}",
                description="Every New England music venue on the site, A to Z: find rooms near you, by genre, or that take open bookings.",
            ),
        },
    )
    return apply_cookie_action(request, response, geo_filter, cookie_action)
