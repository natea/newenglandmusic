"""
the spotify web api, for finding which spotify artist an artist name on our events is
(match_spotify_artists). it signs in as the app itself (the client credentials flow), so no
visitor signs in and the 5-user cap of spotify's development mode doesn't apply; the app's
owner needs spotify premium all the same.

needs SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET, from the app's page in the spotify
developer dashboard. the secret and tokens go only in headers and request bodies, never in
a url or an error message.
"""

import os
import re
import time

import requests

API_URL = "https://api.spotify.com/v1/"
TOKEN_URL = "https://accounts.spotify.com/api/token"
# spotify publishes no fixed rate limit, only a rolling 30-second window. what blocks a
# development-mode app for a day is the number of searches, not their pace: about 650 half
# a second apart (2026-10-27) and about 680 two seconds apart (2026-10-28) each got a 24-hour
# block. so the daily job caps the searches (bin/daily.sh), and the spacing only stays polite
MIN_SECONDS_BETWEEN_REQUESTS = 0.5
MAX_TRIES = 3
# a longer Retry-After means the app is blocked for hours: stop, rather than wait it out
MAX_RETRY_WAIT_SECONDS = 60
TIMEOUT_SECONDS = 20
# development mode caps search results at 10
SEARCH_LIMIT = 10
# open.spotify.com/artist/<id>, open.spotify.com/intl-de/artist/<id>?si=..., spotify:artist:<id>
ARTIST_ID_RE = re.compile(
    r"^(?:https?://open\.spotify\.com/(?:intl-[a-z-]+/)?artist/|spotify:artist:)([A-Za-z0-9]+)(?:[/?#].*)?$"
)


class SpotifyError(Exception):
    pass


class SpotifyBusy(SpotifyError):
    """still rate limited after MAX_TRIES"""


class SpotifyBlocked(SpotifyBusy):
    """rate limited for longer than MAX_RETRY_WAIT_SECONDS: no request is worth making for hours"""


def credentials():
    """(client id, client secret), or None when spotify isn't configured"""
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if client_id and client_secret:
        return client_id, client_secret
    return None


def parse_artist_id(text):
    """the artist id in a spotify artist url or uri, or None"""
    match = ARTIST_ID_RE.match((text or "").strip())
    return match.group(1) if match else None


def error_message(response):
    """spotify's own explanation of a failed request, without anything we sent"""
    try:
        error = response.json().get("error")
    except (ValueError, AttributeError):
        return ""
    if isinstance(error, dict):
        return error.get("message") or ""
    # the token endpoint answers {"error": "invalid_client", "error_description": ...}
    return str(error or "")


class SpotifyClient:
    def __init__(self, client_id, client_secret, session=None, sleep=time.sleep, clock=time.monotonic):
        self.session = session or requests.Session()
        self.auth = (client_id, client_secret)
        self.sleep = sleep
        self.clock = clock
        self.last_request_at = None
        self.token = None
        self.token_expires_at = 0

    def throttle(self):
        if self.last_request_at is not None:
            wait = self.last_request_at + MIN_SECONDS_BETWEEN_REQUESTS - self.clock()
            if wait > 0:
                self.sleep(wait)
        self.last_request_at = self.clock()

    def access_token(self):
        if self.token and self.clock() < self.token_expires_at:
            return self.token
        try:
            response = self.session.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=self.auth,
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as e:
            raise SpotifyError(f"token: {type(e).__name__}")
        if response.status_code != 200:
            raise SpotifyError(f"token: HTTP {response.status_code} {error_message(response)}".strip())
        data = response.json()
        self.token = data["access_token"]
        # renew a minute early, so a request never goes out with a token about to expire
        self.token_expires_at = self.clock() + data.get("expires_in", 3600) - 60
        return self.token

    def get(self, path, **params):
        refreshed = False
        attempt = 0
        while True:
            self.throttle()
            headers = {"Authorization": f"Bearer {self.access_token()}"}
            try:
                response = self.session.get(
                    API_URL + path, params=params, headers=headers, timeout=TIMEOUT_SECONDS
                )
            except requests.RequestException as e:
                raise SpotifyError(f"{path}: {type(e).__name__}")
            if response.status_code == 200:
                return response.json()
            if response.status_code == 401 and not refreshed:
                # the token expired early or was revoked: get a new one, once
                self.token = None
                refreshed = True
                continue
            if response.status_code != 429:
                raise SpotifyError(
                    f"{path}: HTTP {response.status_code} {error_message(response)}".strip()
                )
            attempt += 1
            wait = retry_after(response, attempt)
            if wait > MAX_RETRY_WAIT_SECONDS:
                raise SpotifyBlocked(f"{path}: rate limited; spotify asks to wait {wait / 3600:.1f} hours")
            if attempt >= MAX_TRIES:
                raise SpotifyBusy(f"{path}: still rate limited after {MAX_TRIES} tries")
            self.sleep(wait)

    def search_artists(self, name):
        """spotify artists matching a name, as [{"id", "name"}], best first"""
        data = self.get("search", q=name, type="artist", limit=SEARCH_LIMIT)
        items = (data.get("artists") or {}).get("items") or []
        return [{"id": item["id"], "name": item["name"]} for item in items if item and item.get("id")]


def retry_after(response, attempt):
    """the wait spotify asks for, or else 1, 2, 4... seconds"""
    try:
        return max(float(response.headers.get("Retry-After")), 0)
    except (TypeError, ValueError):
        return 2 ** (attempt - 1)
