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


WIKIPEDIA_FIXTURES = Path(__file__).parent / "fixtures" / "wikipedia"
SPEEDY_ORTIZ_WIKIDATA = "Q17091953"


def load_wikipedia(name):
    return json.loads((WIKIPEDIA_FIXTURES / f"{name}.json").read_text())


class FakeWikipediaSession:
    """
    a requests session answering wikidata's entities, wikipedia's summaries and commons'
    licences from recorded responses (and claims or commons answers a test passes), for
    core.wikipedia.Wikipedia; anything else is a 404
    """

    def __init__(self, summaries=None, titles=None, status=200, claims=None, commons=None):
        self.summaries = {"Speedy_Ortiz": load_wikipedia("summary-speedy-ortiz"), "Pile": load_wikipedia("summary-pile"), **(summaries or {})}
        self.titles = {SPEEDY_ORTIZ_WIKIDATA: "Speedy Ortiz", "Q892329": "Bonerama", "Q485416": "Anamanaguchi", **(titles or {})}
        # {qid: {"P18": "file.jpg", ...}}; recorded items' claims unless a test passes its own
        self.claims = {
            qid: {prop: [c["mainsnak"]["datavalue"]["value"] for c in claims_] for prop, claims_ in load_wikipedia(f"entity-{qid}")["entities"][qid]["claims"].items()}
            for qid in ("Q892329", "Q485416")
        }
        self.claims.update(claims or {})
        # {file name: commons query answer}
        self.commons = {"Bonerama2006.jpg": load_wikipedia("commons-bonerama2006"), "Anamanaguchi.jpg": load_wikipedia("commons-anamanaguchi"), **(commons or {})}
        self.status = status
        self.requests = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.requests.append((url, params, headers))
        if self.status != 200:
            return FakeResponse(self.status, {})
        if url.startswith("https://www.wikidata.org/"):
            qid = params["ids"]
            title = self.titles.get(qid)
            claims = {
                prop: [{"mainsnak": {"datavalue": {"value": value}}, "rank": "normal"} for value in (values if isinstance(values, list) else [values])]
                for prop, values in self.claims.get(qid, {}).items()
            }
            sitelinks = {"enwiki": {"site": "enwiki", "title": title}} if title else {}
            return FakeResponse(200, {"entities": {qid: {"id": qid, "sitelinks": sitelinks, "claims": claims}}})
        if url.startswith("https://commons.wikimedia.org/"):
            answer = self.commons.get(params["titles"].removeprefix("File:"))
            return FakeResponse(200, copy.deepcopy(answer)) if answer else FakeResponse(200, {"query": {"pages": {"-1": {"missing": ""}}}})
        title = url.rsplit("/", 1)[-1]
        summary = self.summaries.get(title)
        return FakeResponse(200, copy.deepcopy(summary)) if summary else FakeResponse(404, {})


class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self.data = data

    def json(self):
        return self.data


def fake_wikipedia(**kwargs):
    from core.wikipedia import Wikipedia

    session = FakeWikipediaSession(**kwargs)
    return Wikipedia(session=session, sleep=lambda seconds: None), session
