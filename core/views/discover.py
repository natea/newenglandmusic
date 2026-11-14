"""
the band discovery deck at /discover (add-band-discovery-swipe): one card for each live band
or artist with an upcoming approved show and something to play (a YouTube, Apple Music or
Spotify match), ordered by each act's next show, soonest first, with a random order only among
acts playing the same New York day. core/static/core/js/discover.js swipes through it. every
card is rendered into the page, with its shows, so the picker needs no request and the page
works without javascript as a list of cards.

the deck takes the listing's region, state and metro filters (core/geo_filters.py) and its
remembered-filter cookie: it holds acts with an upcoming show at a venue in the chosen areas,
and a card and its picker list only those shows.
"""

import random
from dataclasses import dataclass, field
from itertools import groupby

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import strip_tags
from django.views.decorators.cache import never_cache

from core.artist_matching import normalize
from core.artist_previews import act_previews
from core.event_actions import actions_html
from core.geo_filters import CookieAction, apply_cookie_action, geo_filter_context, geo_filter_for_request, new_england_q
from core.location import location_from_request
from core.models import Band, Event, EventPerformer
from core.opengraph import get_meta
from core.saved_shows import COOKIE_NAME, parse_saved
from core.utils_datemath import NYCTZ, beginning_of_day, get_current_new_york_datetime


@dataclass
class Card:
    act: object
    kind: str
    shows: list = field(default_factory=list)
    previews: dict | None = None

    @property
    def anchor(self):
        """the card's id on the page, from its kind and slug: the same act is one card per kind"""
        return f"{self.kind}s-{self.act.slug}"

    @property
    def place(self):
        act = self.act
        return ", ".join(part for part in (act.city_town, act.state) if part) if act.city_town else ""

    @property
    def next_show(self):
        return self.shows[0]

    @property
    def more_shows(self):
        return len(self.shows) - 1


def upcoming_performances(geo_filter):
    """
    every performance of an approved, uncancelled show from the start of today (the band
    page's bound) at a venue in the filter's areas, with its act and show, in one query. the
    shows come through Event.objects (approved only), not the acts' own related manager
    """
    upcoming = Event.objects.filter(
        new_england_q(prefix="venue__"), starttime__gte=beginning_of_day(get_current_new_york_datetime()), is_cancelled=False
    )
    return (
        EventPerformer.objects.filter(geo_filter.q(prefix="event__venue__"), event__in=upcoming)
        .select_related("artist", "band", "event__venue")
        .order_by("event__starttime", "event__same_time_order_override", "event_id")
    )


def name_venue(event):
    """sets the venue name and town the card shows for a show"""
    venue = None if event.venue_override else event.venue
    # the show's own venue text wins, and a show with no venue still shows
    event.venue_name = strip_tags(event.venue_override) if event.venue_override else (venue.name if venue else "Venue to be announced")
    event.town = venue.location if venue else ""


def deck_cards(request, geo_filter):
    """a card for each live act with an upcoming show and something to play, its shows soonest first"""
    saved = set(parse_saved(request.COOKIES.get(COOKIE_NAME)))
    location = location_from_request(request)
    cards = {}
    for performance in upcoming_performances(geo_filter):
        act = performance.act
        if act.needs_review:
            continue
        kind = "band" if isinstance(act, Band) else "artist"
        event = performance.event
        name_venue(event)
        card = cards.setdefault((kind, act.pk), Card(act, kind))
        # no javascript: the bookmark posts to the server and comes back to this card's copy
        # of the show, so a show on two cards has two anchors
        event.anchor = f"{card.anchor}-event-{event.pk}"
        event.actions = actions_html(event, saved, request.get_full_path(), location, event.anchor)
        card.shows.append(event)
    cards = list(cards.values())
    previews = act_previews(card.act.name for card in cards)
    for card in cards:
        card.previews = previews.get(normalize(card.act.name))
    # an act with nothing to play is left out, in the deck and the list alike
    return [card for card in cards if card.previews]


def order_deck(cards):
    """
    soonest next show first. cards whose next show falls on the same new york calendar day are
    shuffled among themselves, for variety; the day is the new york one, so a late show doesn't
    land on the next utc day. each card's first show is its next, as the shows come in order
    """
    cards = sorted(cards, key=lambda card: card.next_show.starttime)
    ordered = []
    for _, same_day in groupby(cards, key=lambda card: card.next_show.starttime.astimezone(NYCTZ).date()):
        same_day = list(same_day)
        random.shuffle(same_day)
        ordered.extend(same_day)
    return ordered


@never_cache
def discover(request):
    # the filter first, so a request that redirects never builds the deck
    geo_filter, cookie_action = geo_filter_for_request(request)
    if cookie_action == CookieAction.REDIRECT:
        # the redirect target has the filter in its url, so it can't redirect again
        return HttpResponseRedirect(f"{request.path}?{geo_filter.query_string}")
    cards = order_deck(deck_cards(request, geo_filter))
    response = render(
        request,
        "core/discover.html",
        {
            "cards": cards,
            **geo_filter_context(geo_filter),
            "meta": get_meta(
                url=request.path, title=f"Discover bands | {settings.SITE_NAME}",
                description="Flip through the Northeast's bands and artists, hear a taste, and save their shows.",
            ),
        },
    )
    return apply_cookie_action(request, response, geo_filter, cookie_action)
