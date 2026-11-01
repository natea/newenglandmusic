from django import template
from django.utils.safestring import mark_safe

from core.event_actions import actions_html, with_actions
from core.location import location_from_request
from core.saved_shows import COOKIE_NAME, parse_saved

register = template.Library()


def saved_ids(request):
    """the visitor's saved shows, parsed once per request"""
    if not hasattr(request, "_saved_show_ids"):
        request._saved_show_ids = set(parse_saved(request.COOKIES.get(COOKIE_NAME)))
    return request._saved_show_ids


@register.simple_tag(takes_context=True)
def event_html(context, event):
    """the event's stored html, with its icon row and distance for this visitor"""
    request = context.get("request")
    saved = saved_ids(request) if request else set()
    next_url = request.get_full_path() if request else "/"
    location = location_from_request(request)
    return mark_safe(with_actions(event.get_baked_html, event, saved, next_url, location))


@register.simple_tag(takes_context=True)
def event_actions(context, event):
    """the event's icon row alone, for a compact row that shows none of its stored html"""
    request = context.get("request")
    saved = saved_ids(request) if request else set()
    next_url = request.get_full_path() if request else "/"
    return actions_html(event, saved, next_url, location_from_request(request))
