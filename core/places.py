"""
looks up venues on google places, with the places api (new) text search -- the same api
world-cup-watch-parties uses. needs GOOGLE_PLACES_API_KEY, restricted in the google cloud
console to the places api (new).

the fields requested decide the price: these are "pro" fields (5,000 free requests a
month, then $32 per 1,000).

google's terms allow storing a place id indefinitely and its coordinates for 30 days, and
nothing else: a search result's name, address and status are used while a lookup runs
(to judge the match, and report closed venues) but never saved. place_details refreshes
a stored id's coordinates (see lookup_venue_places --refresh-stale), and place_name shows
an admin a review venue's place, to judge the match: it's shown, never saved.
"""

import time

import requests

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"
PRO_FIELDS = (
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.businessStatus",
    "places.addressComponents",
)
# only what a refresh stores or reports
DETAILS_FIELDS = ("id", "location", "businessStatus")
# the name alone, for the venue admin (a "pro" field: one request per review venue looked at)
NAME_FIELDS = ("displayName",)
MAX_RESULTS = 3
BIAS_RADIUS_METERS = 30_000
MIN_SECONDS_BETWEEN_REQUESTS = 0.2
MAX_RETRIES = 2
TIMEOUT_SECONDS = 20


class PlacesError(Exception):
    pass


class PlaceNotFound(PlacesError):
    """the place id is obsolete, or the place was removed"""


def to_place_dict(place):
    location = place.get("location") or {}
    state = next(
        (
            component.get("shortText", "")
            for component in place.get("addressComponents") or []
            if "administrative_area_level_1" in component.get("types", [])
        ),
        "",
    )
    return {
        "id": place.get("id", ""),
        "name": (place.get("displayName") or {}).get("text", ""),
        "address": place.get("formattedAddress", ""),
        "state": state,
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "business_status": place.get("businessStatus", ""),
    }


class PlacesClient:
    def __init__(self, api_key, session=None, sleep=time.sleep, clock=time.monotonic):
        self.api_key = api_key
        self.session = session or requests.Session()
        self.sleep = sleep
        self.clock = clock
        self.last_request_at = None

    def throttle(self):
        if self.last_request_at is not None:
            wait = self.last_request_at + MIN_SECONDS_BETWEEN_REQUESTS - self.clock()
            if wait > 0:
                self.sleep(wait)
        self.last_request_at = self.clock()

    def request(self, method, url, what, field_mask, **kwargs):
        """the json response; retries network errors, 429 and 5xx"""
        headers = {
            # in a header rather than the url, so it can't end up in an error message
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": ",".join(field_mask),
        }
        for attempt in range(MAX_RETRIES + 1):
            self.throttle()
            try:
                response = self.session.request(
                    method, url, headers=headers, timeout=TIMEOUT_SECONDS, **kwargs
                )
            except requests.RequestException as e:
                error = f"{what}: {type(e).__name__}"
            else:
                if response.status_code == 200:
                    return response.json()
                error = f"{what}: HTTP {response.status_code}"
                if response.status_code == 404:
                    raise PlaceNotFound(error)
                if response.status_code != 429 and response.status_code < 500:
                    raise PlacesError(error)
            if attempt < MAX_RETRIES:
                self.sleep(2**attempt)
        raise PlacesError(error)

    def search_place(self, text, bias_latitude=None, bias_longitude=None):
        """the top few places for a text search, as dicts (see to_place_dict)"""
        body = {"textQuery": text, "pageSize": MAX_RESULTS}
        if bias_latitude is not None and bias_longitude is not None:
            body["locationBias"] = {
                "circle": {
                    "center": {"latitude": bias_latitude, "longitude": bias_longitude},
                    "radius": BIAS_RADIUS_METERS,
                }
            }
        data = self.request("POST", SEARCH_URL, "places search", PRO_FIELDS, json=body)
        return [to_place_dict(place) for place in data.get("places") or []]

    def place_details(self, place_id):
        """a stored place's current id, coordinates and status"""
        place = self.request(
            "GET", DETAILS_URL.format(place_id=place_id), "place details", DETAILS_FIELDS
        )
        location = place.get("location") or {}
        return {
            "id": place.get("id", place_id),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "business_status": place.get("businessStatus", ""),
        }

    def place_name(self, place_id):
        """a place's name on google right now"""
        place = self.request("GET", DETAILS_URL.format(place_id=place_id), "place details", NAME_FIELDS)
        return (place.get("displayName") or {}).get("text", "")
