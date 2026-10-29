"""
sets and clears the visitor's location (core/location.py) for the events' distance labels:
the location form sends a typed zip code or town as q, or "use my location" sends lat and
lon. the location goes in a cookie, never the database, and the visitor goes back to the
page they came from.
"""

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme

from ..location import COOKIE_MAX_AGE, COOKIE_NAME, DEVICE_LABEL, encode, resolve, rounded

NOT_FOUND = "We couldn't find {place}. Try a town name, such as \"Somerville, MA\", or another ZIP code."
NO_POSITION = "Your device didn't give a location. Try typing your ZIP code or town instead."


def back_to(request):
    """the local page to return to; anything else goes home"""
    next_url = request.GET.get("next") or request.POST.get("next") or "/"
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return next_url
    return "/"


def set_location(request):
    params = request.POST if request.method == "POST" else request.GET
    next_url = back_to(request)
    response = HttpResponseRedirect(next_url)
    if "clear" in params:
        response.delete_cookie(COOKIE_NAME)
        return response
    if params.get("error") == "position":
        messages.warning(request, NO_POSITION)
        return response
    if params.get("lat") and params.get("lon"):
        try:
            location = rounded(params["lat"], params["lon"], DEVICE_LABEL)
        except ValueError:
            location = None
        if location is None or not (-90 <= location.latitude <= 90 and -180 <= location.longitude <= 180):
            messages.warning(request, NO_POSITION)
            return response
    else:
        found = resolve(params.get("q", ""))
        if isinstance(found, list):
            return render(request, "core/location_choices.html", {"choices": found, "next": next_url, "q": params.get("q", "")})
        if found is None:
            messages.warning(request, NOT_FOUND.format(place=f"“{params.get('q', '').strip()}”" if params.get("q", "").strip() else "that place"))
            return response
        location = found
    response.set_cookie(COOKIE_NAME, encode(location), max_age=COOKIE_MAX_AGE, samesite="Lax")
    return response
