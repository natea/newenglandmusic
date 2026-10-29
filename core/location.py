"""
a visitor's location, and how far things are from it: the location form's lookup of a zip
code or town in the census gazetteer (CensusPlace, loaded by load_census_gazetteer), the
cookie that remembers it, and straight-line distances for the events' "(0.5 mi away)"
labels. the venue list can sort by the same distances:

    location = location_from_request(request)
    sorted(venues, key=lambda venue: miles(location.point, venue.exact_location))

the cookie holds only the label and the coordinates rounded to three places (about 100 m);
nothing about a visitor's location is kept on the server.
"""

import math
import re
from dataclasses import dataclass
from urllib.parse import quote, unquote

from core.artist_evidence import STATE_NAMES
from core.artist_matching import normalize

COOKIE_NAME = "near"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60
PLACES = 3
EARTH_RADIUS_MILES = 3958.8
DEVICE_LABEL = "your location"
MAX_CHOICES = 10
STATE_CODES = {normalize(name): code for code, name in STATE_NAMES.items()}


@dataclass(frozen=True)
class Location:
    label: str
    latitude: float
    longitude: float

    @property
    def point(self):
        return self.latitude, self.longitude


def rounded(latitude, longitude, label):
    return Location(label, round(float(latitude), PLACES), round(float(longitude), PLACES))


def state_code(text):
    """"MA", "ma" or "Massachusetts" -> "MA"; None for anything else"""
    text = (text or "").strip()
    if text.upper() in STATE_NAMES:
        return text.upper()
    return STATE_CODES.get(normalize(text))


def covered_states():
    from core.models import Venue

    return set(Venue.objects.exclude(state="").values_list("state", flat=True).distinct())


def venue_towns():
    """the (normalized town, state) of every venue: the towns visitors here most likely mean"""
    from core.models import Venue

    rows = Venue.objects.exclude(city_town="").values_list("city_town", "state").distinct()
    return {(normalize(town), state) for town, state in rows}


def town_label(place):
    return f"{place.name}, {place.state}"


def resolve(text):
    """
    what a visitor typed, as a Location, a list of Locations to choose from (a name several
    towns share), or None when nothing matches
    """
    from core.models import CensusPlace

    text = (text or "").strip()
    if re.fullmatch(r"\d{5}", text):
        place = CensusPlace.objects.filter(kind=CensusPlace.Kind.ZIP, name=text).first()
        return rounded(place.latitude, place.longitude, text) if place else None
    town, _, state = text.rpartition(",") if "," in text else (text, "", "")
    key = normalize(town)
    if not key:
        return None
    towns = CensusPlace.objects.filter(kind=CensusPlace.Kind.TOWN, search_key=key)
    if state:
        code = state_code(state)
        place = towns.filter(state=code).first() if code else None
        return rounded(place.latitude, place.longitude, town_label(place)) if place else None
    matches = list(towns.order_by("state"))
    if not matches:
        return None
    # a town with venues first ("Somerville" means MA here, not ME or NJ), then any in a
    # state the site covers, then anywhere
    with_venues = [place for place in matches if (place.search_key, place.state) in venue_towns()]
    covered = [place for place in matches if place.state in covered_states()]
    candidates = (with_venues if len(with_venues) == 1 else None) or covered or matches
    if len(candidates) == 1:
        place = candidates[0]
        return rounded(place.latitude, place.longitude, town_label(place))
    return [rounded(place.latitude, place.longitude, town_label(place)) for place in candidates[:MAX_CHOICES]]


def encode(location):
    """the cookie's value: label|latitude|longitude"""
    return quote(f"{location.label}|{location.latitude:.{PLACES}f}|{location.longitude:.{PLACES}f}", safe="")


def decode(value):
    """the Location in a cookie value, or None when it isn't one"""
    try:
        label, latitude, longitude = unquote(value or "").rsplit("|", 2)
        latitude, longitude = float(latitude), float(longitude)
    except ValueError:
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or not label.strip():
        return None
    return rounded(latitude, longitude, label.strip()[:80])


def location_from_request(request):
    """the visitor's Location from their cookie, or None; read once per request"""
    if request is None:
        return None
    if not hasattr(request, "_near_location"):
        request._near_location = decode(request.COOKIES.get(COOKIE_NAME))
    return request._near_location


def miles(a, b):
    """the straight-line (haversine) distance in miles between two (latitude, longitude)"""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def format_miles(distance):
    """"0.5 mi away", "144 mi away", or "less than 0.1 mi away" """
    if distance < 0.1:
        return "less than 0.1 mi away"
    tenths = round(distance, 1)
    if tenths < 10:
        return f"{tenths:.1f} mi away"
    return f"{round(distance)} mi away"
