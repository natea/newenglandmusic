"""
the band discovery deck at /discover (add-band-discovery-swipe): one card for each live band
or artist with an upcoming approved show, in a random order for each visit, which core/static/
core/js/discover.js swipes through. every card is rendered into the page, with its shows, so
the picker needs no request and the page works without javascript as a list of cards.

the deck ignores the remembered area filter, as /saved does, and never changes it.
"""

import random
from dataclasses import dataclass, field

from django.conf import settings
from django.shortcuts import render
from django.utils.html import strip_tags
from django.views.decorators.cache import never_cache

from core.artist_matching import normalize
from core.artist_previews import act_previews
from core.event_actions import actions_html
from core.location import location_from_request
from core.models import Band, Event, EventPerformer
from core.opengraph import get_meta
from core.saved_shows import COOKIE_NAME, parse_saved
from core.utils_datemath import beginning_of_day, get_current_new_york_datetime
from core.views.act_page import photo_of

PHOTO_WIDTH = 480


@dataclass
class Card:
    act: object
    kind: str
    shows: list = field(default_factory=list)
    previews: dict | None = None
    photo: object = None

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

    @property
    def has_player(self):
        return bool(self.previews)


def upcoming_performances():
    """
    every performance of an approved, uncancelled show from the start of today (the band
    page's bound), with its act and show, in one query. the shows come through Event.objects
    (approved only), not the acts' own related manager
    """
    upcoming = Event.objects.filter(
        starttime__gte=beginning_of_day(get_current_new_york_datetime()), is_cancelled=False
    )
    return (
        EventPerformer.objects.filter(event__in=upcoming)
        .select_related("artist", "band", "event__venue")
        .order_by("event__starttime", "event__same_time_order_override", "event_id")
    )


def name_venue(event):
    """sets the venue name and town the card shows for a show"""
    venue = None if event.venue_override else event.venue
    # the show's own venue text wins, and a show with no venue still shows
    event.venue_name = strip_tags(event.venue_override) if event.venue_override else (venue.name if venue else "Venue to be announced")
    event.town = venue.location if venue else ""


def deck_cards(request):
    """a card for each live act with an upcoming show, its shows soonest first"""
    saved = set(parse_saved(request.COOKIES.get(COOKIE_NAME)))
    location = location_from_request(request)
    cards = {}
    for performance in upcoming_performances():
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
        event.actions = actions_html(event, saved, request.path, location, event.anchor)
        card.shows.append(event)
    cards = list(cards.values())
    previews = act_previews(card.act.name for card in cards)
    for card in cards:
        card.previews = previews.get(normalize(card.act.name))
        # a photo only stands in when there is no player
        card.photo = None if card.previews else photo_of(card.act, PHOTO_WIDTH)
    return cards


@never_cache
def discover(request):
    cards = deck_cards(request)
    random.shuffle(cards)
    return render(
        request,
        "core/discover.html",
        {
            "cards": cards,
            "meta": get_meta(
                url=request.path, title=f"Discover bands | {settings.SITE_NAME}",
                description="Flip through the Northeast's bands and artists, hear a taste, and save their shows.",
            ),
        },
    )
