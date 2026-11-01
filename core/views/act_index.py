"""
the a–z index of bands and artists at /bands (add-act-index-and-search): every live act,
bands and artists together, grouped by first letter ("#" for digits and symbols, a leading
"The" ignored), each with its kind, home town and next upcoming show. acts held for review
aren't listed; /artists redirects here.
"""

import unicodedata

from django.conf import settings
from django.db.models import Min, Q
from django.shortcuts import redirect, render

from core.models import Artist, Band
from core.opengraph import get_meta
from core.utils_datemath import beginning_of_day, get_current_new_york_datetime
from core.views.act_page import origin_of

LETTERS = ["#", *"ABCDEFGHIJKLMNOPQRSTUVWXYZ"]

# entries on one "page" of the index: two columns of twenty, read down one then the other
# without scrolling back up, each page headed by its first and last names as guide words
PAGE_SIZE = 40

# the countries musicbrainz gives as an act's area, shortened for the index's narrow columns
SHORT_AREAS = {"United States": "US", "United Kingdom": "UK"}


def sort_name(name):
    """the name as it's filed: "The Atlantics" under A"""
    name = name.strip()
    return name[4:].lstrip() if name.lower().startswith("the ") else name


def index_name(name):
    """the name as an index prints it: "The Atlantics" as "Atlantics, The", so it reads where it's filed"""
    filed = sort_name(name)
    return f"{filed}, {name.strip()[:3]}" if filed != name.strip() else name


def letter_of(name):
    """the index letter: the first letter, accents dropped ("É" under E), else "#" """
    first = unicodedata.normalize("NFKD", sort_name(name)[:1]).encode("ascii", "ignore").decode().upper()
    return first if first in LETTERS[1:] else "#"


def short_origin(act):
    """the act's town, or its musicbrainz area with "United States" as "US" """
    origin = origin_of(act)
    return SHORT_AREAS.get(origin, origin)


def pages_of(acts):
    """a letter's acts in pages of PAGE_SIZE: [(first name, last name, acts)]"""
    return [
        (page[0].index_name, page[-1].index_name, page)
        for page in (acts[start:start + PAGE_SIZE] for start in range(0, len(acts), PAGE_SIZE))
    ]


def live_acts():
    """every live band and artist, with next_show (its next upcoming approved show's start, or None)"""
    today = beginning_of_day(get_current_new_york_datetime())
    upcoming = Q(performances__event__is_approved=True, performances__event__starttime__gte=today)
    acts = []
    for model in (Band, Artist):
        acts.extend(
            model.objects.filter(needs_review=False)
            .annotate(next_show=Min("performances__event__starttime", filter=upcoming))
            .only("name", "slug", "city_town", "state", "area")
        )
    acts.sort(key=lambda act: sort_name(act.name).casefold())
    return acts


def act_index(request):
    groups = {letter: [] for letter in LETTERS}
    for act in live_acts():
        act.index_name = index_name(act.name)
        act.kind = "band" if isinstance(act, Band) else "artist"
        act.place = short_origin(act)
        groups[letter_of(act.name)].append(act)
    return render(
        request,
        "core/act_index.html",
        {
            "groups": [(letter, pages_of(acts)) for letter, acts in groups.items() if acts],
            "rail": [(letter, bool(acts)) for letter, acts in groups.items()],
            "count": sum(len(acts) for acts in groups.values()),
            # a show in another year carries its year
            "this_year": str(get_current_new_york_datetime().year),
            "meta": get_meta(
                url=request.path, title=f"Bands & artists | {settings.SITE_NAME}",
                description="Every band and artist on the site, A to Z, with their next show in the Northeast.",
            ),
        },
    )


def artists_index(request):
    # one index for both kinds: a visitor looks for a name, not a kind
    return redirect("act_index", permanent=True)
