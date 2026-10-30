"""
the public page of a band (/bands/<slug>) or an artist (/artists/<slug>), set as a filed
index card (add-band-pages): the name on a purple tab, the next show right under it, then
members or bands, links, a photo, the bio and every upcoming show. a field the act has
nothing for isn't drawn, and a page missing a photo, bio or links invites the act to send
them.

credits travel with what they credit: wikipedia's text (cc by-sa 4.0), a commons photo's
author and licence, and musicbrainz's genres (cc by-nc-sa).
"""

import os
from dataclasses import dataclass
from urllib.parse import quote, unquote

from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core.event_actions import actions_html
from core.location import location_from_request
from core.models import Artist, Band, Event
from core.opengraph import get_meta
from core.saved_shows import COOKIE_NAME, parse_saved
from core.utils_datemath import beginning_of_day, get_current_new_york_datetime
from core.wikipedia import commons_file_page, commons_thumbnail

PHOTO_WIDTH = 640
HEADSHOT_WIDTH = 96
# former members past this many fold behind a summary, so the bio stays near the top
FORMER_SHOWN = 3


@dataclass
class Photo:
    src: str
    page: str
    author: str
    license: str
    license_url: str


def photo_of(act, width):
    if not act.photo_file:
        return None
    return Photo(
        commons_thumbnail(act.photo_file, width), commons_file_page(act.photo_file), act.photo_author,
        act.photo_license, act.photo_license_url,
    )


def years(membership):
    """"1993–2012", "2013", "since 2019", "until 2015", or "" """
    begin, end = membership.begin_year, membership.end_year
    if begin and end and begin == end:
        return str(begin)
    if begin and end:
        return f"{begin}–{end}"
    if begin:
        return f"since {begin}"
    return f"until {end}" if end else ""


def upcoming_shows(act):
    """the act's upcoming approved shows, soonest first"""
    field = "performers__band" if isinstance(act, Band) else "performers__artist"
    return list(
        # Event.objects: approved events only
        Event.objects.filter(**{field: act}, starttime__gte=beginning_of_day(get_current_new_york_datetime()))
        .select_related("venue")
        .order_by("starttime", "same_time_order_override")
    )


def links_of(act):
    return [
        (label, url) for label, url in (
            ("Website", act.website), ("Bandcamp", act.bandcamp_url),
            ("Instagram", act.instagram_url), ("YouTube", act.youtube_url),
        ) if url
    ]


def members_of(band):
    """(current, former): each (artist, role, years, headshot), current members first"""
    current, former = [], []
    for membership in band.memberships.select_related("artist").order_by("begin_year", "artist__name"):
        entry = (membership.artist, membership.role, years(membership), photo_of(membership.artist, HEADSHOT_WIDTH))
        (former if membership.is_former else current).append(entry)
    return current, former


def bands_of(artist):
    """(band, role, years) for each band the artist is in, current ones first"""
    memberships = list(artist.memberships.select_related("band").order_by("-begin_year", "band__name"))
    ordered = [m for m in memberships if not m.is_former] + [m for m in memberships if m.is_former]
    return [(m.band, m.role, years(m)) for m in ordered]


def origin_of(act):
    """"Boise, ID", or musicbrainz's area when the act has no town"""
    if act.city_town:
        return f"{act.city_town}, {act.state}" if act.state else act.city_town
    return act.area


def invitation(request, act):
    """an email to the site's contact address, for a page missing its photo, bio or links"""
    email = os.environ.get("API_CONTACT_EMAIL", "").strip()
    if not email or (act.photo_file and (act.wikipedia_extract or act.disambiguation) and links_of(act)):
        return None
    subject = f"{act.name} on {settings.SITE_NAME}"
    body = f"About {request.build_absolute_uri()}\n\nPhoto (and who took it), bio, and links:\n"
    return f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"


def wikipedia_title(act):
    """the article's own title, from its url: "Built to Spill", not our "Built To Spill" """
    return unquote(act.wikipedia_url.rstrip("/").rsplit("/", 1)[-1]).replace("_", " ") or act.name


def act_page(request, act):
    shows = upcoming_shows(act)
    # each show carries the calendar's own actions: calendar file, google, map, share, save
    saved = set(parse_saved(request.COOKIES.get(COOKIE_NAME)))
    location = location_from_request(request)
    for event in shows:
        event.actions = actions_html(event, saved, request.path, location)
    is_band = isinstance(act, Band)
    current, former = members_of(act) if is_band else ([], [])
    origin = origin_of(act)
    meta_bits = [bit for bit in (
        "Band" if is_band else "Artist", ", ".join(act.genres[:2]), origin,
        # a person's musicbrainz begin date is their birth, not when they started playing
        f"since {act.begin_date[:4]}" if is_band and act.begin_date[:4].isdigit() else "",
    ) if bit]
    description = act.disambiguation or f"{act.name}: upcoming shows in the Northeast, members and links."
    if act.wikipedia_extract:
        description = act.wikipedia_extract.split(". ")[0][:200]
    return render(
        request,
        "core/band.html",
        {
            "act": act,
            "is_band": is_band,
            "meta_line": " · ".join(meta_bits),
            "shows": shows,
            "next_show": shows[0] if shows else None,
            "more_shows": max(len(shows) - 1, 0),
            "current_members": current,
            "former_members": former[:FORMER_SHOWN] if len(former) > FORMER_SHOWN + 1 else former,
            "more_former_members": former[FORMER_SHOWN:] if len(former) > FORMER_SHOWN + 1 else [],
            "members_have_headshots": any(entry[3] for entry in current + former),
            "bands": [] if is_band else bands_of(act),
            "links": links_of(act),
            "photo": photo_of(act, PHOTO_WIDTH),
            "wikipedia_title": wikipedia_title(act) if act.wikipedia_url else "",
            "invitation": invitation(request, act),
            # thin pages stay out of search results until they have a show to point to
            "noindex": not shows,
            "meta": get_meta(url=request.path.rstrip("/"), title=f"{act.name} | {settings.SITE_NAME}", description=description),
        },
    )


def band_page(request, slug):
    return act_page(request, get_object_or_404(Band, slug=slug))


def artist_page(request, slug):
    return act_page(request, get_object_or_404(Artist, slug=slug))


def act_url(act):
    return reverse("band_page" if isinstance(act, Band) else "artist_page", kwargs={"slug": act.slug})
