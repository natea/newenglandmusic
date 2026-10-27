from django import template
from django.utils.safestring import mark_safe

from core.event_actions import with_actions
from core.saved_shows import COOKIE_NAME, parse_saved

register = template.Library()


def saved_ids(request):
    """the visitor's saved shows, parsed once per request"""
    if not hasattr(request, "_saved_show_ids"):
        request._saved_show_ids = set(parse_saved(request.COOKIES.get(COOKIE_NAME)))
    return request._saved_show_ids


@register.simple_tag(takes_context=True)
def event_html(context, event):
    """the event's stored html, with its icon row for this visitor"""
    request = context.get("request")
    saved = saved_ids(request) if request else set()
    next_url = request.get_full_path() if request else "/"
    return mark_safe(with_actions(event.get_baked_html, event, saved, next_url))
