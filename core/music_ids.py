"""
youtube channels linked to an artist's spotify or apple music id in the open music
databases, wikidata and musicbrainz: the strongest evidence match_youtube_artists has that a
channel is the artist's own, since these are links between ids that people curate, not
guesses from a name. both are free and need no key.

wikidata is asked in batches with one sparql query. musicbrainz asks for one request a
second and a user agent that says who we are (musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting),
so it's paced here.
"""

import re
import time

import requests

from core.user_agent import USER_AGENT

WIKIDATA_URL = "https://query.wikidata.org/sparql"
MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/"
TIMEOUT_SECONDS = 30
WIKIDATA_BATCH = 200
MUSICBRAINZ_SECONDS_BETWEEN_REQUESTS = 1.1
# musicbrainz answers 503 when it's busy or we're too fast: wait 2, 4, then 8 seconds
MUSICBRAINZ_TRIES = 4
# wikidata's properties: spotify artist id, apple music artist id (us), youtube channel id
SPOTIFY_PROPERTY, APPLE_PROPERTY, YOUTUBE_PROPERTY = "P1902", "P2850", "P2397"
# only ids of these shapes go into a query, so nothing we didn't make can change it
SPOTIFY_ID_RE = re.compile(r"^[0-9A-Za-z]{22}$")
APPLE_ID_RE = re.compile(r"^\d+$")
CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
CHANNEL_URL_RE = re.compile(r"^https?://(?:www\.)?youtube\.com/channel/(UC[\w-]{22})/?$")


class MusicIdsError(Exception):
    pass


class MusicBrainzBusy(MusicIdsError):
    """musicbrainz kept answering 503: it's overloaded, or throttling us, for a while"""


class MusicIds:
    def __init__(self, session=None, sleep=time.sleep, clock=time.time):
        self.session = session or requests.Session()
        self.sleep = sleep
        self.clock = clock
        self.last_musicbrainz_at = None

    def wikidata_channels(self, spotify_ids=(), apple_ids=()):
        """{("spotify" or "apple", id): {channel ids}} for the ids wikidata links to youtube"""
        spotify_ids = sorted({i for i in spotify_ids if SPOTIFY_ID_RE.match(i)})
        apple_ids = sorted({i for i in apple_ids if APPLE_ID_RE.match(i)})
        found = {}
        for kind, prop, ids in (("spotify", SPOTIFY_PROPERTY, spotify_ids), ("apple", APPLE_PROPERTY, apple_ids)):
            for start in range(0, len(ids), WIKIDATA_BATCH):
                values = " ".join(f'"{i}"' for i in ids[start : start + WIKIDATA_BATCH])
                query = f"SELECT ?id ?yt WHERE {{ VALUES ?id {{ {values} }} ?item wdt:{prop} ?id ; wdt:{YOUTUBE_PROPERTY} ?yt . }}"
                for row in self.sparql(query):
                    channel = (row.get("yt") or {}).get("value", "")
                    if CHANNEL_ID_RE.match(channel):
                        found.setdefault((kind, row["id"]["value"]), set()).add(channel)
        return found

    def sparql(self, query):
        try:
            # posted, as a long batch of ids is too long for a url
            response = self.session.post(
                WIKIDATA_URL,
                data={"query": query},
                headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as e:
            raise MusicIdsError(f"wikidata: {type(e).__name__}")
        if response.status_code != 200:
            raise MusicIdsError(f"wikidata: HTTP {response.status_code}")
        return ((response.json() or {}).get("results") or {}).get("bindings") or []

    def musicbrainz_channels(self, spotify_id):
        """the youtube channel ids of the musicbrainz artist linked to this spotify artist"""
        if not SPOTIFY_ID_RE.match(spotify_id or ""):
            return set()
        url = self.musicbrainz("url", resource=f"https://open.spotify.com/artist/{spotify_id}", inc="artist-rels")
        if url is None:
            return set()
        artists = {r["artist"]["id"] for r in url.get("relations") or [] if (r.get("artist") or {}).get("id")}
        if len(artists) != 1:
            # a spotify page linked to several artists says nothing about any one of them
            return set()
        artist = self.musicbrainz(f"artist/{artists.pop()}", inc="url-rels") or {}
        channels = set()
        for relation in artist.get("relations") or []:
            match = CHANNEL_URL_RE.match(((relation.get("url") or {}).get("resource")) or "")
            if match:
                channels.add(match.group(1))
        return channels

    def musicbrainz(self, path, **params):
        """musicbrainz's answer, or None when it has no such thing"""
        for attempt in range(1, MUSICBRAINZ_TRIES + 1):
            if self.last_musicbrainz_at is not None:
                wait = self.last_musicbrainz_at + MUSICBRAINZ_SECONDS_BETWEEN_REQUESTS - self.clock()
                if wait > 0:
                    self.sleep(wait)
            self.last_musicbrainz_at = self.clock()
            try:
                response = self.session.get(
                    MUSICBRAINZ_URL + path,
                    params={**params, "fmt": "json"},
                    headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                    timeout=TIMEOUT_SECONDS,
                )
            except requests.RequestException as e:
                raise MusicIdsError(f"musicbrainz: {type(e).__name__}")
            if response.status_code == 404:
                return None
            if response.status_code == 200:
                return response.json()
            if response.status_code != 503:
                raise MusicIdsError(f"musicbrainz: HTTP {response.status_code}")
            if attempt < MUSICBRAINZ_TRIES:
                self.sleep(2**attempt)
        raise MusicBrainzBusy(f"musicbrainz: HTTP 503 after {MUSICBRAINZ_TRIES} tries")
