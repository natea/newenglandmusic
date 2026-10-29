from django import template

from core.location import location_from_request

register = template.Library()


@register.inclusion_tag("core/location_form.html", takes_context=True)
def location_form(context):
    """the zip code / town form for the distance labels; hidden until the census data is loaded"""
    from core.models import CensusPlace

    request = context.get("request")
    return {
        "show": CensusPlace.objects.exists(),
        "location": location_from_request(request),
        "next": request.get_full_path() if request else "/",
    }
