"""
what the site's search covers, one kind at a time (add-act-index-and-search): bands and
artists, venues and upcoming shows, each with how it matches what was typed and how a match
is shown: its kind, its name, a quiet detail line and where it links. the search results
page and the suggestions (/search/suggest) both walk KINDS, so they never disagree, and
resources join later as one more kind. the results page lists every show its full-text
search finds, past ones too, in place of the upcoming shows suggested here.

names are matched on their normalized form (core.artist_matching.normalize: case, accents,
punctuation and a leading "the" ignored), so "o'brien" finds O'Brien's and "bell" Belly.
acts held for review and inactive venues are never matched.
"""

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

from django.db.models import Case, IntegerField, Min, Q, Value, When
from django.utils import timezone

from core.artist_matching import normalize
from core.geo_filters import new_england_q
from core.models import Artist, Band, Event, Venue
from core.utils_datemath import beginning_of_day, get_current_new_york_datetime
from core.views.act_index import SHORT_AREAS, sort_name
from core.views.act_page import origin_of


@dataclass
class Match:
    kind: str  # "band", "artist", "venue" or "show"
    name: str
    detail: str
    url: str
    # an act's next upcoming show, its page reference on the results page
    when: datetime | None = None

    @property
    def kind_label(self):
        return self.kind.capitalize()

    @property
    def index_kind(self):
        """the kind on the results page's grey line; a venue's heading already says it"""
        return self.kind if self.kind in ("band", "artist") else ""

    @property
    def index_place(self):
        """the town on the results page's grey line, "United States" as "US" """
        return SHORT_AREAS.get(self.detail, self.detail)

    def as_dict(self, group):
        return {"kind": self.kind, "group": group, "name": self.name, "detail": self.detail, "url": self.url}


def starts_first(key):
    """0 for a name that starts with what's typed, else 1: "bel" puts Belly before Campbell"""
    return Case(When(name_key__startswith=key, then=Value(0)), default=Value(1), output_field=IntegerField())


def acts(query, limit):
    """live bands and artists whose names contain the query, those starting with it first, A to Z"""
    key = normalize(query)
    if not key:
        return []
    today = beginning_of_day(get_current_new_york_datetime())
    upcoming = Q(performances__event__is_approved=True, performances__event__starttime__gte=today)
    upcoming &= new_england_q(prefix="performances__event__venue__")
    found = []
    for model, kind in ((Band, "band"), (Artist, "artist")):
        found.extend(
            (act, kind) for act in model.objects.filter(needs_review=False, name_key__contains=key)
            .annotate(starts=starts_first(key), next_show=Min("performances__event__starttime", filter=upcoming))
            .only("name", "slug", "city_town", "state", "area")
            .order_by("starts", "name_key")[:limit]
        )
    found.sort(key=lambda pair: (pair[0].starts, sort_name(pair[0].name).casefold()))
    return [Match(kind, act.name, origin_of(act), act.get_absolute_url(), act.next_show) for act, kind in found[:limit]]


def venue_url(venue):
    """the venue's page once venues have pages (add-venue-pages); until then, a search for its shows"""
    return "/?" + urlencode({"s": venue.name})


def venues(query, limit):
    """active venues whose names contain the query, those starting with it first, A to Z"""
    key = normalize(query)
    if not key:
        return []
    found = [
        venue for venue in Venue.objects.exclude(is_active=False).only("name", "city_town", "state", "neighborhood").order_by("name")
        if key in normalize(venue.name)
    ]
    found.sort(key=lambda venue: not normalize(venue.name).startswith(key))
    return [Match("venue", venue.name, venue.location, venue_url(venue)) for venue in found[:limit]]


def shows(query, limit):
    """upcoming approved shows whose title or artists contain the query, soonest first"""
    query = query.strip()
    if not query:
        return []
    today = beginning_of_day(get_current_new_york_datetime())
    found = (
        # Event.objects: approved events only
        Event.objects.filter(
            Q(title__icontains=query) | Q(artists__icontains=query), new_england_q(prefix="venue__"), starttime__gte=today
        )
        .select_related("venue").order_by("starttime")[:limit]
    )
    return [Match("show", event.title_and_artists, show_detail(event), f"/event/{event.pk}") for event in found]


def show_detail(event):
    """"Nov 7 · Paradise Rock Club" """
    start = timezone.localtime(event.starttime)
    when = f"{start:%b} {start.day}"
    venue = event.venue.name if event.venue else event.venue_override
    return f"{when} · {venue}" if venue else when


# (group label, the kind's matches for a query and a limit), in the order they're shown
KINDS = [
    ("Bands & artists", acts),
    ("Venues", venues),
    ("Shows", shows),
]
