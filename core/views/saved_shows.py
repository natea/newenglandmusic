from django.db.models.functions import TruncDate
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models import Event
from ..opengraph import get_meta
from ..saved_shows import COOKIE_MAX_AGE, COOKIE_NAME, format_saved, parse_saved, toggle_saved
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
    # the map gets a toggle only when some listed show can have a pin: map/map.html pins the
    # uncancelled events that carry data-venue-lnglat, which a located venue gives them
    has_mappable = any(
        event.venue and not event.is_cancelled
        and event.venue.exact_latitude is not None and event.venue.exact_longitude is not None
        for event in events
    )
    response = render(
        request,
        "core/saved.html",
        {
            "group": group,
            "has_mappable": has_mappable,
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


# no csrf check: the toggle's only effect is one public event id in the visitor's own cookie,
# which isn't worth a csrf token in each of a listing's thousand forms. post only, so links
# and prefetching can't set it off
@csrf_exempt
@require_POST
def toggle_saved_show(request, event_id):
    """
    saves or unsaves a show without javascript: the bookmark's form posts here, and the
    visitor goes back to where they were (next, on this site only), at the event
    """
    saved = parse_saved(request.COOKIES.get(COOKIE_NAME))
    if event_id in saved or Event.all_objects.filter(pk=event_id).exists():
        saved = toggle_saved(saved, event_id)
    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = "/"
    response = HttpResponseRedirect(next_url)
    if saved:
        response.set_cookie(COOKIE_NAME, format_saved(saved), max_age=COOKIE_MAX_AGE, samesite="Lax")
    else:
        # an empty value would be written as '""'
        response.delete_cookie(COOKIE_NAME, samesite="Lax")
    return response
