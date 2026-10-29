"""
the last.fm api, read behind the scenes as evidence of which act an artist name means
(resolve_artists_with_lastfm, match_youtube_artists): an artist page's musicbrainz id,
listener count and bio, and its most-played track. nothing from last.fm is shown on the
site or stored: it's read during a run and discarded (see openspec/specs/lastfm-artist-evidence).

needs LASTFM_API_KEY. last.fm takes the key only as the api_key query parameter, so no
request url is ever printed, logged or put in an error message. last.fm publishes no limit
beyond "several calls a second" risking suspension, so requests go half a second apart.
"""

import os
import time

import requests

from core.user_agent import user_agent

API_URL = "https://ws.audioscrobbler.com/2.0/"
MIN_SECONDS_BETWEEN_REQUESTS = 0.5
TIMEOUT_SECONDS = 20
NOT_FOUND = 6
# rate limit exceeded, and a suspended key: no request is worth making for a while
STOP_ERRORS = {26, 29}


class LastFmError(Exception):
    pass


class LastFmStopped(LastFmError):
    """last.fm rate-limited us or suspended the key: stop for this run"""


def api_key():
    return os.environ.get("LASTFM_API_KEY") or None


class LastFm:
    def __init__(self, key, session=None, sleep=time.sleep, clock=time.monotonic):
        self.key = key
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

    def call(self, method, **params):
        """last.fm's answer, or None when it has no such artist or track"""
        self.throttle()
        try:
            response = self.session.get(
                API_URL,
                params={"method": method, "api_key": self.key, "format": "json", **params},
                headers={"User-Agent": user_agent()},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as e:
            # the exception's text can hold the url, and so the key
            raise LastFmError(f"{method}: {type(e).__name__}")
        try:
            data = response.json()
        except ValueError:
            raise LastFmError(f"{method}: HTTP {response.status_code}")
        error = data.get("error") if isinstance(data, dict) else None
        if error is None and response.status_code == 200:
            return data
        message = f"{method}: last.fm error {error}: {data.get('message', '')}".strip() if error else f"{method}: HTTP {response.status_code}"
        if error == NOT_FOUND:
            return None
        if error in STOP_ERRORS:
            raise LastFmStopped(message)
        raise LastFmError(message)

    def artist_info(self, name):
        """{"mbid", "listeners", "bio"} for the name's page, as written, or None"""
        data = self.call("artist.getInfo", artist=name, autocorrect=0)
        artist = (data or {}).get("artist")
        if not artist:
            return None
        try:
            listeners = int((artist.get("stats") or {}).get("listeners") or 0)
        except ValueError:
            listeners = 0
        return {
            "mbid": artist.get("mbid") or "",
            "listeners": listeners,
            "bio": (artist.get("bio") or {}).get("summary") or "",
        }

    def top_track(self, name):
        """{"name", "album"} for the page's most-played track, or None"""
        data = self.call("artist.getTopTracks", artist=name, autocorrect=0, limit=1)
        tracks = ((data or {}).get("toptracks") or {}).get("track") or []
        if isinstance(tracks, dict):
            tracks = [tracks]
        if not tracks or not tracks[0].get("name"):
            return None
        track = tracks[0]["name"]
        info = self.call("track.getInfo", artist=name, track=track, autocorrect=0)
        album = (((info or {}).get("track") or {}).get("album") or {}).get("title") or ""
        return {"name": track, "album": album}


def client():
    """a client with the environment's key; call only when api_key() is set"""
    return LastFm(api_key())
