"""
the apple music api, for finding which apple music artist an artist name on our events is,
and that artist's most popular song (match_apple_music_artists), for the listing's apple
music play buttons.

it needs a musickit key from an apple developer program membership: APPLE_MUSIC_TEAM_ID,
APPLE_MUSIC_KEY_ID and APPLE_MUSIC_PRIVATE_KEY (the .p8 file's text). from those it signs its
own developer token, an ES256 jwt good for an hour, sent only in the Authorization header of
requests made here on the server. the key and the token never go in a page, url, log or
error message. catalog requests need no visitor to sign in.

APPLE_MUSIC_PREVIEWS ("true") separately decides whether the listing shows the buttons, so
matches can be reviewed in the admin first.
"""

import os
import re
import time

import jwt
import requests

API_URL = "https://api.music.apple.com/v1/catalog/us/"
TOKEN_LIFETIME_SECONDS = 3600
# a token is renewed this long before it expires, so none goes out about to lapse
TOKEN_RENEW_SECONDS = 300
# a token says it was issued this long ago: a server whose clock is a little behind ours
# would otherwise see it as issued in the future, and reject it
TOKEN_BACKDATE_SECONDS = 60
# apple doesn't publish its rate limit; this stays polite, and 429s are retried
MIN_SECONDS_BETWEEN_REQUESTS = 0.5
MAX_TRIES = 3
# apple answers about one request in ten with a spurious 401, at any pace, sometimes a few
# in a row (measured 2026-10-27: the same token works again moments later). so a 401 is
# retried with the same token, waiting 2, 4, 8 then 16 seconds, and only one that keeps
# coming back means the credentials are wrong
MAX_AUTH_TRIES = 5
# a longer Retry-After means hours of blocking (as spotify did on 2026-10-27): stop instead
MAX_RETRY_WAIT_SECONDS = 60
TIMEOUT_SECONDS = 20
SEARCH_LIMIT = 10
# music.apple.com/us/artist/the-ballroom-thieves/489634654 (the slug is optional)
ARTIST_ID_RE = re.compile(
    r"^https?://music\.apple\.com/[a-z]{2}/artist/(?:[^/?#]+/)?(\d+)(?:[/?#].*)?$"
)
# a song's url: music.apple.com/us/album/archers/964625535?i=964625539
ALBUM_ID_RE = re.compile(r"/album/(?:[^/?#]+/)?(\d+)")


class AppleMusicError(Exception):
    pass


class AppleMusicBusy(AppleMusicError):
    """still rate limited after MAX_TRIES"""


class AppleMusicBlocked(AppleMusicBusy):
    """rate limited for longer than MAX_RETRY_WAIT_SECONDS: no request is worth making for hours"""


class AppleMusicAuthError(AppleMusicError):
    """apple rejected the developer token: the credentials are wrong or revoked"""


def credentials():
    """(team id, key id, private key pem), or None when apple music isn't configured"""
    team_id = os.environ.get("APPLE_MUSIC_TEAM_ID")
    key_id = os.environ.get("APPLE_MUSIC_KEY_ID")
    private_key = os.environ.get("APPLE_MUSIC_PRIVATE_KEY")
    if team_id and key_id and private_key:
        # environment variables often hold the pem's newlines as \n
        return team_id, key_id, private_key.replace("\\n", "\n")
    return None


def previews_enabled():
    """whether the listing shows apple music buttons: configured, and switched on"""
    return bool(credentials()) and os.environ.get("APPLE_MUSIC_PREVIEWS", "").lower() == "true"


def parse_artist_id(text):
    """the artist id in an apple music artist url, or None"""
    match = ARTIST_ID_RE.match((text or "").strip())
    return match.group(1) if match else None


def error_message(response):
    """apple's own explanation of a failed request, without anything we sent"""
    try:
        errors = response.json().get("errors") or []
    except (ValueError, AttributeError):
        return ""
    return "; ".join(str(error.get("detail") or error.get("title") or "") for error in errors if error)


class AppleMusicClient:
    def __init__(self, team_id, key_id, private_key, session=None, sleep=time.sleep, clock=time.time):
        self.team_id = team_id
        self.key_id = key_id
        self.private_key = private_key
        self.session = session or requests.Session()
        self.sleep = sleep
        self.clock = clock
        self.last_request_at = None
        self.token = None
        self.token_expires_at = 0

    def developer_token(self):
        now = self.clock()
        if self.token and now < self.token_expires_at - TOKEN_RENEW_SECONDS:
            return self.token
        issued = int(now) - TOKEN_BACKDATE_SECONDS
        self.token_expires_at = issued + TOKEN_LIFETIME_SECONDS
        self.token = jwt.encode(
            {"iss": self.team_id, "iat": issued, "exp": self.token_expires_at},
            self.private_key,
            algorithm="ES256",
            headers={"kid": self.key_id},
        )
        return self.token

    def throttle(self):
        if self.last_request_at is not None:
            wait = self.last_request_at + MIN_SECONDS_BETWEEN_REQUESTS - self.clock()
            if wait > 0:
                self.sleep(wait)
        self.last_request_at = self.clock()

    def get(self, path, **params):
        attempt = 0
        rejected = 0
        while True:
            self.throttle()
            headers = {"Authorization": f"Bearer {self.developer_token()}"}
            try:
                response = self.session.get(
                    API_URL + path, params=params, headers=headers, timeout=TIMEOUT_SECONDS
                )
            except requests.RequestException as e:
                raise AppleMusicError(f"{path}: {type(e).__name__}")
            if response.status_code == 200:
                return response.json()
            if response.status_code == 401:
                rejected += 1
                if rejected < MAX_AUTH_TRIES:
                    # spurious more often than not: wait, then try the same token again
                    self.sleep(2**rejected)
                    continue
                raise AppleMusicAuthError(
                    f"{path}: HTTP 401 -- apple rejected the developer token; check APPLE_MUSIC_TEAM_ID, "
                    "APPLE_MUSIC_KEY_ID and APPLE_MUSIC_PRIVATE_KEY"
                )
            if response.status_code != 429:
                raise AppleMusicError(f"{path}: HTTP {response.status_code} {error_message(response)}".strip())
            attempt += 1
            wait = retry_after(response, attempt)
            if wait > MAX_RETRY_WAIT_SECONDS:
                raise AppleMusicBlocked(f"{path}: rate limited; apple asks to wait {wait / 3600:.1f} hours")
            if attempt >= MAX_TRIES:
                raise AppleMusicBusy(f"{path}: still rate limited after {MAX_TRIES} tries")
            self.sleep(wait)

    def search_artists(self, name):
        """apple music artists matching a name, as [{"id", "name"}], best first"""
        data = self.get("search", term=name, types="artists", limit=SEARCH_LIMIT)
        items = ((data.get("results") or {}).get("artists") or {}).get("data") or []
        return [
            {"id": item["id"], "name": (item.get("attributes") or {}).get("name", "")}
            for item in items
            if item and item.get("id")
        ]

    def top_song(self, artist_id):
        """
        the artist's most popular song, as {"song_id", "album_id", "name", "album_name"}, or
        None. only the ids are stored; the names are for match_youtube_artists to find the
        same recording on youtube during its run
        """
        data = self.get(f"artists/{artist_id}/view/top-songs", limit=1)
        for song in data.get("data") or []:
            attributes = song.get("attributes") or {}
            # the album is in the song's url, which saves a request for its albums
            match = ALBUM_ID_RE.search(attributes.get("url", ""))
            if song.get("id") and match:
                return {
                    "song_id": song["id"],
                    "album_id": match.group(1),
                    "name": attributes.get("name", ""),
                    "album_name": attributes.get("albumName", ""),
                }
        return None


def retry_after(response, attempt):
    """the wait apple asks for, or else 1, 2, 4... seconds"""
    try:
        return max(float(response.headers.get("Retry-After")), 0)
    except (TypeError, ValueError):
        return 2 ** (attempt - 1)


def client():
    """a client from the environment's credentials; call only when credentials() is set"""
    return AppleMusicClient(*credentials())
