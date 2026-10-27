import datetime
import hashlib

from django.http import HttpResponse, HttpResponseNotModified
from django.utils import timezone

from ..calendar_feeds import calendar
from ..geo_filters import parse_geo_filter
from ..models import Event

# from shows of the past week, so a calendar refreshed mid-week keeps the weekend's,
# to the next 90 days, which keeps the whole northeast's feed to about a megabyte
PAST = datetime.timedelta(days=7)
AHEAD = datetime.timedelta(days=90)


def calendar_feed(request):
    """
    an icalendar feed of the upcoming shows in an area, from the listing's region, state and
    metro parameters (none: every area). only the url decides the area: the visitor's
    remembered filter is neither read nor written, so a subscription stays what it was
    """
    geo_filter = parse_geo_filter(request.GET)
    now = timezone.now()
    events = (
        # Event.objects: approved events only
        Event.objects.select_related("venue")
        .filter(geo_filter.q(prefix="venue__"), starttime__gte=now - PAST, starttime__lt=now + AHEAD)
        .order_by("starttime", "same_time_order_override", "pk")
    )
    body = calendar(events, " / ".join(area.label for area in geo_filter.areas))
    etag = f'"{hashlib.sha1(body).hexdigest()}"'
    if etag in [tag.strip() for tag in request.headers.get("If-None-Match", "").split(",")]:
        response = HttpResponseNotModified()
    else:
        response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = 'inline; filename="new-england-music.ics"'
    response["ETag"] = etag
    response["Cache-Control"] = "public, max-age=3600"
    return response
