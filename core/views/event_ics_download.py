from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from ..models import Event
from ..utils import get_ics_string_from_event


def event_ics_download(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    response = HttpResponse(
        get_ics_string_from_event(event), content_type="text/calendar"
    )
    response["Content-Disposition"] = "inline; filename=event.ics"
    if posthog_client := settings.POSTHOG_MW_CLIENT:
        posthog_client.capture("event_ics_downloaded")
    return response
