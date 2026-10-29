"""
a venue's neighborhood, from openstreetmap (lookup_venue_neighborhoods): nominatim finds the
venue by its own name and town, and its address names the neighborhood; where openstreetmap
marks neighborhoods only as points (new york, dc), overpass finds the nearest one.

nothing from google is sent: the venue is found by name, and its location is openstreetmap's
own. the data is odbl, storable with credit ("© OpenStreetMap contributors", in the footer).
nominatim allows one request a second with a contact user agent (core/user_agent.py);
overpass's public servers are often busy, so it's retried, then tried on a mirror.
"""

import re
import time

import requests

from core.artist_matching import normalize
from core.location import miles
from core.user_agent import user_agent

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URLS = ("https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter")
TIMEOUT_SECONDS = 30
NOMINATIM_SECONDS_BETWEEN_REQUESTS = 1.0
OVERPASS_WAITS = (5, 15, 45)
OVERPASS_RETRY_STATUSES = {429, 502, 503, 504}
NEAREST_RADIUS_M = 1500
# the address keys that name a neighborhood, the smallest first. the first full run
# (2026-10-29) preferred "suburb", which was too broad in philadelphia ("North Philadelphia"
# for the fillmore in fishtown) and wrong in new haven ("Dixwell" for every downtown venue,
# whose "neighbourhood" is "Downtown")
NAME_KEYS = ("neighbourhood", "quarter", "suburb", "city_district")
# the address keys a venue's town can be in: new york's venues' "town" is their borough
TOWN_KEYS = ("city", "town", "village", "hamlet", "municipality", "suburb", "borough", "city_district")
BOROUGHS = {"manhattan", "brooklyn", "queens", "bronx", "staten island"}
# the towns where openstreetmap marks neighborhoods only as points, so an address never names
# them and overpass is asked for the nearest one. everywhere else, an address without one
# means there's none worth naming (a dry run on 2026-10-29 asked overpass for small-town
# venues, and its busy servers cost two minutes each)
POINT_NEIGHBORHOOD_TOWNS = {("new york", "NY"), ("washington", "DC")} | {(borough, "NY") for borough in BOROUGHS}


def has_point_neighborhoods(town, state):
    return (normalize(town), state.upper()) in POINT_NEIGHBORHOOD_TOWNS


class OsmError(Exception):
    pass


class NominatimBlocked(OsmError):
    """nominatim refused us (429 or 403): no request is worth making this run"""


class OverpassUnavailable(OsmError):
    """overpass and its mirror stayed busy"""


def usable(name, town):
    """whether an address value can be a venue's neighborhood"""
    if not name or not name.strip():
        return False
    key = normalize(name)
    return not (
        # "Main Street Historic District No. 2" (hartford) too
        "historic district" in key
        # administrative districts, not neighborhoods ("Manhattan Community Board 3")
        or "community board" in key
        or key == normalize(town)
        or key in BOROUGHS
        or key.endswith(" county")
    )


def choose_name(address, town):
    """the neighborhood an address names for a venue in `town`, or None"""
    for key in NAME_KEYS:
        if usable(address.get(key), town):
            return address[key].strip()
    return None


def names_match(venue_name, place_name):
    """the place's name is the venue's, or contains it as whole words"""
    venue, place = normalize(venue_name), normalize(place_name)
    return bool(venue) and (venue == place or f" {venue} " in f" {place} ")


def in_town(address, town, state):
    """whether an address is in the venue's town and state"""
    code = (address.get("ISO3166-2-lvl4") or "").upper()
    if code and code != f"US-{state.upper()}":
        return False
    wanted = normalize(town)
    return any(normalize(address.get(key, "")) == wanted for key in TOWN_KEYS)


def accepted_result(results, venue_name, town, state):
    """the first search result that's the venue, or None"""
    for result in results:
        address = result.get("address") or {}
        name = result.get("name") or ""
        if names_match(venue_name, name) and in_town(address, town, state):
            return result
    return None


class OsmClient:
    def __init__(self, session=None, sleep=time.sleep, clock=time.monotonic):
        self.session = session or requests.Session()
        self.sleep = sleep
        self.clock = clock
        self.last_nominatim_at = None

    def search(self, venue_name, town, state):
        """nominatim's results for the venue, with address details"""
        if self.last_nominatim_at is not None:
            wait = self.last_nominatim_at + NOMINATIM_SECONDS_BETWEEN_REQUESTS - self.clock()
            if wait > 0:
                self.sleep(wait)
        self.last_nominatim_at = self.clock()
        params = {
            "q": f"{venue_name}, {town}, {state}",
            "countrycodes": "us",
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 5,
        }
        try:
            response = self.session.get(
                NOMINATIM_URL, params=params, headers={"User-Agent": user_agent()}, timeout=TIMEOUT_SECONDS
            )
        except requests.RequestException as e:
            raise OsmError(f"nominatim: {type(e).__name__}")
        if response.status_code in (403, 429):
            raise NominatimBlocked(f"nominatim: HTTP {response.status_code}")
        if response.status_code != 200:
            raise OsmError(f"nominatim: HTTP {response.status_code}")
        return response.json() or []

    def nearest_neighborhood(self, latitude, longitude, town):
        """the usable name of the nearest neighborhood point within NEAREST_RADIUS_M, or None"""
        query = (
            f"[out:json][timeout:25];node(around:{NEAREST_RADIUS_M},{latitude},{longitude})"
            '["place"~"^(neighbourhood|suburb|quarter)$"];out;'
        )
        data = self.overpass(query)
        here = (latitude, longitude)
        nodes = [
            node for node in data.get("elements") or []
            if usable((node.get("tags") or {}).get("name"), town) and "lat" in node and "lon" in node
        ]
        if not nodes:
            return None
        nearest = min(nodes, key=lambda node: miles(here, (node["lat"], node["lon"])))
        return nearest["tags"]["name"].strip()

    def overpass(self, query):
        for url in OVERPASS_URLS:
            for attempt, wait in enumerate((0, *OVERPASS_WAITS)):
                if wait:
                    self.sleep(wait)
                try:
                    response = self.session.post(
                        url, data={"data": query}, headers={"User-Agent": user_agent()}, timeout=TIMEOUT_SECONDS
                    )
                except requests.RequestException:
                    continue
                if response.status_code == 200:
                    return response.json() or {}
                if response.status_code not in OVERPASS_RETRY_STATUSES:
                    break
        raise OverpassUnavailable("overpass: busy on every try, and on its mirror")
