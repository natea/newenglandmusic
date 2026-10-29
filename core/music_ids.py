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

from core.user_agent import user_agent

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
SPOTIFY_ARTIST_URL_RE = re.compile(r"^https?://open\.spotify\.com/artist/([0-9A-Za-z]{22})/?$")
APPLE_ARTIST_URL_RE = re.compile(r"^https?://(?:itunes|music)\.apple\.com/[a-z]{2}/artist/(?:[^/?#]+/)?(?:id)?(\d+)(?:[/?#].*)?$")
# a city's state is usually two "part of" links up (city, county, state); five allows for
# boroughs and districts
AREA_STEPS = 5
SEARCH_LIMIT = 10
# characters lucene gives a meaning, escaped in a searched name
LUCENE_SPECIAL_RE = re.compile(r'[+\-&|!(){}\[\]^"~*?:\\/]')
MBID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


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
        # area id -> its state's iso code, as found this run
        self.areas = {}

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
                headers={"Accept": "application/sparql-results+json", "User-Agent": user_agent()},
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

    def artist(self, mbid):
        """
        {"name", "areas", "spotify", "apple"} for a musicbrainz artist: its name, the names of
        its area and begin area, and the spotify and apple music artist ids its links give.
        None when musicbrainz has no such artist
        """
        if not MBID_RE.match(mbid or ""):
            return None
        data = self.musicbrainz(f"artist/{mbid}", inc="url-rels")
        if data is None:
            return None
        spotify, apple = set(), set()
        for relation in data.get("relations") or []:
            resource = ((relation.get("url") or {}).get("resource")) or ""
            for pattern, found in ((SPOTIFY_ARTIST_URL_RE, spotify), (APPLE_ARTIST_URL_RE, apple)):
                match = pattern.match(resource)
                if match:
                    found.add(match.group(1))
        areas = [
            {"id": area.get("id") or "", "name": area["name"]}
            for area in (data.get("area"), data.get("begin-area"))
            if area and area.get("name")
        ]
        return {"name": data.get("name") or "", "areas": areas, "spotify": spotify, "apple": apple}

    def search_artists(self, name, kind, limit=SEARCH_LIMIT):
        """
        musicbrainz's candidates for an artist ("person") or band ("group") with this name:
        its search, with the name quoted, which also matches aliases. each is musicbrainz's
        own dict ("id", "name", "type", "area", "aliases", "life-span"…)
        """
        escaped = LUCENE_SPECIAL_RE.sub(lambda m: "\\" + m.group(0), name)
        query = f'artist:"{escaped}" AND type:{kind}'
        data = self.musicbrainz("artist", query=query, limit=limit) or {}
        return data.get("artists") or []

    def artist_details(self, mbid):
        """
        a musicbrainz artist with its relationships (a band's members), url links and
        genres, or None when there's no such artist
        """
        if not MBID_RE.match(mbid or ""):
            return None
        return self.musicbrainz(f"artist/{mbid}", inc="artist-rels+url-rels+genres+aliases")

    def area_subdivision(self, area_id, steps=AREA_STEPS):
        """
        the iso 3166-2 code ("US-MA", "CA-ON") of the state or province an area is in,
        following musicbrainz's "part of" links up from a city or county; "" when there's
        none within `steps`. a town's name alone says nothing: Windsor, Ontario and
        Windsor, Connecticut are both "Windsor"
        """
        seen = []
        while area_id and MBID_RE.match(area_id) and len(seen) < steps:
            if area_id in self.areas:
                code = self.areas[area_id]
                break
            seen.append(area_id)
            data = self.musicbrainz(f"area/{area_id}", inc="area-rels") or {}
            codes = data.get("iso-3166-2-codes") or []
            if codes:
                code = codes[0]
                break
            parents = [
                r["area"]["id"]
                for r in data.get("relations") or []
                if r.get("type") == "part of" and r.get("direction") == "backward" and (r.get("area") or {}).get("id")
            ]
            area_id = parents[0] if parents else ""
        else:
            code = ""
        for visited in seen:
            self.areas[visited] = code
        return code

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
                    headers={"User-Agent": user_agent(), "Accept": "application/json"},
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
