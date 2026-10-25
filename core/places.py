"""
looks up venues on google places, with the places api (new) text search -- the same api
world-cup-watch-parties uses. needs GOOGLE_PLACES_API_KEY, restricted in the google cloud
console to the places api (new).

the fields requested decide the price: the defaults are "pro" fields (5,000 free requests
a month, then $32 per 1,000); website and phone are "enterprise" fields (1,000 free a
month, then $35 per 1,000), so they're only requested with contact=True.
"""

import time

import requests

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PRO_FIELDS = (
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.businessStatus",
    "places.googleMapsUri",
    "places.addressComponents",
)
CONTACT_FIELDS = ("places.websiteUri", "places.nationalPhoneNumber")
MAX_RESULTS = 3
BIAS_RADIUS_METERS = 30_000
MIN_SECONDS_BETWEEN_REQUESTS = 0.2
MAX_RETRIES = 2
TIMEOUT_SECONDS = 20


class PlacesError(Exception):
    pass


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
        "maps_url": place.get("googleMapsUri", ""),
        "website": place.get("websiteUri", ""),
        "phone": place.get("nationalPhoneNumber", ""),
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

    def search_place(self, text, bias_latitude=None, bias_longitude=None, contact=False):
        """the top few places for a text search, as dicts (see to_place_dict)"""
        body = {"textQuery": text, "pageSize": MAX_RESULTS}
        if bias_latitude is not None and bias_longitude is not None:
            body["locationBias"] = {
                "circle": {
                    "center": {"latitude": bias_latitude, "longitude": bias_longitude},
                    "radius": BIAS_RADIUS_METERS,
                }
            }
        headers = {
            # in a header rather than the url, so it can't end up in an error message
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": ",".join(PRO_FIELDS + (CONTACT_FIELDS if contact else ())),
        }

        for attempt in range(MAX_RETRIES + 1):
            self.throttle()
            try:
                response = self.session.post(
                    SEARCH_URL, json=body, headers=headers, timeout=TIMEOUT_SECONDS
                )
            except requests.RequestException as e:
                error = f"places search: {type(e).__name__}"
            else:
                if response.status_code == 200:
                    places = response.json().get("places") or []
                    return [to_place_dict(place) for place in places]
                error = f"places search: HTTP {response.status_code}"
                if response.status_code != 429 and response.status_code < 500:
                    raise PlacesError(error)
            if attempt < MAX_RETRIES:
                self.sleep(2**attempt)
        raise PlacesError(error)
