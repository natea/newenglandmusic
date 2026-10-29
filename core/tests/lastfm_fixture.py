"""
a fake last.fm api for tests: answers artist pages, top tracks and track lookups from
hand-written data in last.fm's documented shapes (fixtures/lastfm/), and remembers what
was asked, so no request leaves the test. the key is a made-up one.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.lastfm import LastFm

FIXTURES = Path(__file__).parent / "fixtures" / "lastfm"
TEST_KEY = "fake-lastfm-key-0123456789"
CONFIGURED = {"LASTFM_API_KEY": TEST_KEY}


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


def page(name, mbid="", listeners=1000, bio=""):
    """an artist.getInfo answer"""
    return {"artist": {"name": name, "mbid": mbid, "stats": {"listeners": str(listeners)}, "bio": {"summary": bio}}}


def response(status, data):
    return SimpleNamespace(status_code=status, json=lambda: data, headers={})


class FakeLastFm:
    """
    pages answer artist.getInfo (artist name -> data, or a list given in turn), tracks answer
    artist.getTopTracks (name -> data) and albums answer track.getInfo ((name, track) -> data).
    anything else is error 6, as last.fm answers an unknown artist
    """

    def __init__(self, pages=None, tracks=None, albums=None):
        self.pages = dict(pages or {})
        self.tracks = dict(tracks or {})
        self.albums = dict(albums or {})
        self.requests = []
        self.sleeps = []
        self.now = 1000.0

    def get(self, url, params=None, headers=None, timeout=None):
        self.requests.append(SimpleNamespace(url=url, params=dict(params or {}), headers=headers or {}))
        method, name = params["method"], params.get("artist")
        if method == "artist.getInfo":
            answer = self.pages.get(name)
        elif method == "artist.getTopTracks":
            answer = self.tracks.get(name)
        else:
            answer = self.albums.get((name, params.get("track")))
        if isinstance(answer, list):
            answer = answer.pop(0)
        if answer is None:
            answer = fixture("not_found.json")
        if hasattr(answer, "status_code"):
            return answer
        return response(200, answer)

    def add_song(self, name, track, album="", bio=""):
        """a page for `name` whose most-played track is `track`, on `album` (none if blank)"""
        self.pages[name] = page(name, bio=bio)
        self.tracks[name] = {"toptracks": {"track": [{"name": track, "artist": {"name": name}}]}}
        found = {"name": track, "artist": {"name": name}}
        if album:
            found["album"] = {"artist": name, "title": album}
        self.albums[(name, track)] = {"track": found}

    @property
    def methods(self):
        return [r.params["method"] for r in self.requests]

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def client(self, key=TEST_KEY):
        return LastFm(key, session=self, sleep=self.sleep, clock=self.clock)

    def patch(self, where):
        """use this fake wherever `where` makes a LastFm client"""
        return mock.patch(where, lambda key: self.client(key))
