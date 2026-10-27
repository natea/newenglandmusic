"""
a fake spotify for tests: answers the token endpoint and artist searches from the
hand-written fixtures in fixtures/spotify/ (fake ids, no real tokens), and remembers what
was asked. no request leaves the test.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.spotify import SpotifyClient

FIXTURES = Path(__file__).parent / "fixtures" / "spotify"
CREDENTIALS = {"SPOTIFY_CLIENT_ID": "fake-client-id", "SPOTIFY_CLIENT_SECRET": "fake-client-secret"}
NO_RESULTS = {"artists": {"items": []}}


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


def response(status, data, headers=None):
    return SimpleNamespace(status_code=status, json=lambda: data, headers=headers or {})


def rate_limited(retry_after=None):
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else {}
    return response(429, fixture("rate_limited.json"), headers)


class FakeSpotify:
    """
    searches answer from `results` (search text -> fixture data, or a list of responses
    given in turn); other searches find nothing
    """

    def __init__(self, results=None):
        self.results = dict(results or {})
        self.searches = []
        self.token_requests = []
        self.sleeps = []
        self.now = 0.0

    def post(self, url, data=None, auth=None, timeout=None):
        self.token_requests.append(SimpleNamespace(url=url, data=data, auth=auth))
        return response(200, fixture("token_client_credentials.json"))

    def get(self, url, params=None, headers=None, timeout=None):
        self.searches.append(SimpleNamespace(url=url, params=params, headers=headers))
        answer = self.results.get(params["q"], NO_RESULTS)
        if isinstance(answer, list):
            return answer.pop(0)
        return response(200, answer)

    # the client's clock and sleep: sleeping moves the clock on, without waiting
    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def client(self, client_id="fake-client-id", client_secret="fake-client-secret"):
        return SpotifyClient(client_id, client_secret, session=self, sleep=self.sleep, clock=self.clock)

    def patch(self, where="core.management.commands.match_spotify_artists.SpotifyClient"):
        """use this fake wherever `where` makes a SpotifyClient"""
        return mock.patch(where, lambda *credentials: self.client(*credentials))
