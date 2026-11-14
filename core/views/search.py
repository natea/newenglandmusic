from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control

from ..geo_filters import new_england_q
from ..models import Event, SearchableStaticPageBit, StaticPage
from ..search_kinds import KINDS, shows
from ..utils_datemath import beginning_of_day, get_current_new_york_datetime

# how many bands and artists, and venues, a results page lists
RESULTS_LIMIT = 50


def search(request):
    query = request.GET.get("s", "").strip()

    if not query:
        return render(request, "core/search.html")

    # https://stackoverflow.com/a/70812950
    search_query = SearchQuery(query)
    search_rank = SearchRank(F("search_vector"), search_query)
    found_static_page_ids = (
        SearchableStaticPageBit.objects.annotate(rank=search_rank)
        .filter(search_vector=search_query)  # Perform full text search on index.
        .values("static_page__id")
        .distinct()
    )
    results_pages = (
        # static page's (overridden) manager should return public pages only,
        # but be double sure here and specify we're only searching public pages
        StaticPage.objects.filter(id__in=found_static_page_ids, is_public=True)
        .order_by("title")
        .all()
    )

    found_events = (
        # the venue, for each event's map icon (core/event_actions.py)
        Event.objects.select_related("venue")
        .filter(new_england_q(prefix="venue__"))
        .annotate(
            search=SearchVector(
                "title",
                "artists",
                "venue__name",
                "venue_override",
                "description",
                "preface",
            )
        )
        # words anywhere, and part of a title or the artists, as the suggestions match
        .filter(Q(search=query) | Q(title__icontains=query) | Q(artists__icontains=query))
        .distinct()
    )
    # upcoming shows first, soonest first; then past ones, newest first
    today = beginning_of_day(get_current_new_york_datetime())
    upcoming_shows = found_events.filter(starttime__gte=today).order_by("starttime")
    past_shows = found_events.filter(starttime__lt=today).order_by("-starttime")

    # bands and artists, then venues, above the shows: the registry's own show search is the
    # suggestions' upcoming-only one, so the page keeps its full-text search of every show
    groups = [(group, find(query, RESULTS_LIMIT)) for group, find in KINDS if find is not shows]

    return render(
        request,
        "core/search.html",
        {
            "query": query,
            # the header's search box shows what was searched (base.html)
            "search_query": query,
            "groups": [(group, matches) for group, matches in groups if matches],
            # a show in another year carries its year
            "this_year": str(today.year),
            "results_pages": results_pages,
            "upcoming_shows": upcoming_shows,
            "past_shows": past_shows,
            # for the search_results_viewed analytics event (core/js/analytics.js)
            "search_counts": search_counts(query, groups, upcoming_shows, past_shows, results_pages),
        },
    )



def search_counts(query, groups, upcoming_shows, past_shows, results_pages):
    """the words searched and how many of each kind matched, as the results page shows them"""
    found = dict(groups)
    counts = {
        "acts": len(found.get("Bands & artists", [])),
        "venues": len(found.get("Venues", [])),
        "upcoming": upcoming_shows.count(),
        "past": past_shows.count(),
        "pages": results_pages.count(),
    }
    return {"query": query, **counts, "total": sum(counts.values())}


# suggestions per kind, and the fewest characters worth suggesting for
SUGGESTIONS_PER_KIND = 5
SUGGEST_MIN_LENGTH = 2


# a minute: typing the same letters again, or going back, needn't ask again
@cache_control(max_age=60, public=True)
def suggest(request):
    """what the search box suggests as you type (core/static/core/js/search-suggest.js), by kind"""
    query = request.GET.get("q", "").strip()
    items = []
    if len(query) >= SUGGEST_MIN_LENGTH:
        for group, find in KINDS:
            items.extend(match.as_dict(group) for match in find(query, SUGGESTIONS_PER_KIND))
    return JsonResponse({"items": items})
