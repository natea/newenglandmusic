"""
a fake musicbrainz for artist enrichment tests, answering from recorded responses
(core/tests/fixtures/musicbrainz/, recorded 2026-10-29) and from candidates a test builds.
nothing reaches the network.
"""

import copy
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "musicbrainz"
SPEEDY_ORTIZ = "4fbf1a3d-a649-4f8e-9ddf-347f6ba2d307"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def candidate(mbid, name, kind="Group", area_id=None, country=None, aliases=()):
    """a search result as musicbrainz gives it"""
    found = {"id": mbid, "name": name, "type": kind, "aliases": [{"name": a} for a in aliases]}
    if area_id:
        found["area"] = {"id": area_id, "name": area_id}
    if country:
        found["country"] = country
    return found


def details(mbid, name, kind="Group", **fields):
    return {"id": mbid, "name": name, "type": kind, "relations": [], "genres": [], **fields}


class FakeMusicBrainz:
    """search_artists, artist_details and area_subdivision, as core.music_ids.MusicIds has them"""

    def __init__(self, searches=None, artists=None, areas=None):
        speedy = load("artist-speedy-ortiz")
        self.searches = {"Speedy Ortiz": load("search-speedy-ortiz")["artists"], **(searches or {})}
        self.artists = {SPEEDY_ORTIZ: speedy, **(artists or {})}
        # area id -> its state's code; speedy ortiz's area is the united states, no state
        self.areas = areas or {}
        self.calls = []

    def search_artists(self, name, kind):
        self.calls.append(("search", name, kind))
        return copy.deepcopy(self.searches.get(name, []))

    def artist_details(self, mbid):
        self.calls.append(("lookup", mbid))
        return copy.deepcopy(self.artists.get(mbid))

    def area_subdivision(self, area_id):
        return self.areas.get(area_id, "")


class FakeLastFm:
    def __init__(self, pages=None):
        self.pages = pages or {}
        self.calls = []

    def artist_info(self, name):
        self.calls.append(name)
        return self.pages.get(name)
