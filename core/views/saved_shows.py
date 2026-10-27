from django.db.models.functions import TruncDate
from django.shortcuts import render

from ..models import Event
from ..opengraph import get_meta
from ..saved_shows import COOKIE_MAX_AGE, COOKIE_NAME, format_saved, parse_saved
from ..utils_datemath import beginning_of_day, get_current_new_york_datetime
from .index import group_events_by_date

# how the page groups shows; venue, artist and location can join "date" later
GROUPINGS = ("date",)


def saved_shows(request):
    """
    the visitor's upcoming saved shows, grouped by date like the homepage, whatever area
    the visitor is browsing. the cookie is rewritten without the shows that can no longer
    happen (past, deleted, unapproved)
    """
    group = request.GET.get("group")
    group = group if group in GROUPINGS else "date"
    saved = parse_saved(request.COOKIES.get(COOKIE_NAME))
    events = list(
        # Event.objects: approved events only
        Event.objects.select_related("venue")
        .filter(pk__in=saved, starttime__gte=beginning_of_day(get_current_new_york_datetime()))
        .order_by("starttime", "same_time_order_override")
        .annotate(date=TruncDate("starttime"))
    )
    grouped = group_events_by_date(events)
    response = render(
        request,
        "core/saved.html",
        {
            "group": group,
            "grouped_events_as_list": [{"date": date, "events": events} for date, events in grouped.items()],
            "meta": get_meta(),
        },
    )
    # keep the visitor's own order (newest saved first) for the shows still to come
    found = {event.pk for event in events}
    kept = [event_id for event_id in saved if event_id in found]
    if kept:
        response.set_cookie(COOKIE_NAME, format_saved(kept), max_age=COOKIE_MAX_AGE, samesite="Lax")
    elif COOKIE_NAME in request.COOKIES:
        response.delete_cookie(COOKIE_NAME, samesite="Lax")
    return response
