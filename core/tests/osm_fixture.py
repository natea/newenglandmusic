"""
a fake nominatim and overpass for tests: answers venue searches and nearest-neighborhood
queries from hand-written data in their documented shapes (fixtures/osm/), and remembers
what was asked, so no request leaves the test.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.neighborhoods import OsmClient

FIXTURES = Path(__file__).parent / "fixtures" / "osm"


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


def response(status, data=None):
    return SimpleNamespace(status_code=status, json=lambda: data, headers={})


class FakeOsm:
    """
    searches answer from `searches` (venue name -> results, or a response, or a list given in
    turn); overpass answers from `overpass` (a list of responses or data, given in turn, the
    last repeated). anything else finds nothing
    """

    def __init__(self, searches=None, overpass=None):
        self.searches = dict(searches or {})
        self.overpass = list(overpass or [fixture("overpass_empty.json")])
        self.requests = []
        self.sleeps = []
        self.now = 1000.0

    def get(self, url, params=None, headers=None, timeout=None):
        self.requests.append(SimpleNamespace(method="GET", url=url, params=dict(params or {}), data=None, headers=headers or {}))
        venue = params["q"].split(",")[0]
        answer = self.searches.get(venue, [])
        if isinstance(answer, list) and answer and hasattr(answer[0], "status_code"):
            answer = answer.pop(0)
        return answer if hasattr(answer, "status_code") else response(200, answer)

    def post(self, url, data=None, headers=None, timeout=None):
        self.requests.append(SimpleNamespace(method="POST", url=url, params={}, data=data, headers=headers or {}))
        answer = self.overpass.pop(0) if len(self.overpass) > 1 else self.overpass[0]
        return answer if hasattr(answer, "status_code") else response(200, answer)

    @property
    def overpass_requests(self):
        return [r for r in self.requests if r.method == "POST"]

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def client(self):
        return OsmClient(session=self, sleep=self.sleep, clock=self.clock)

    def patch(self, where="core.management.commands.lookup_venue_neighborhoods.OsmClient"):
        return mock.patch(where, lambda: self.client())
