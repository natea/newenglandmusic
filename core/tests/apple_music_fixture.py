"""
a fake apple music api for tests: answers artist searches and top-songs views from the
hand-written fixtures in fixtures/apple_music/ (the api's documented shapes, no personal
data), and remembers what was asked. the musickit key is a throwaway one made per test run,
so no real key is used and no request leaves the test.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from core.apple_music import AppleMusicClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

FIXTURES = Path(__file__).parent / "fixtures" / "apple_music"

# a .p8 file holds a pkcs8 p-256 key, as this does
TEST_KEY = ec.generate_private_key(ec.SECP256R1())
TEST_PRIVATE_KEY = TEST_KEY.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()
TEST_PUBLIC_KEY = TEST_KEY.public_key()

CREDENTIALS = {
    "APPLE_MUSIC_TEAM_ID": "FAKETEAM01",
    "APPLE_MUSIC_KEY_ID": "FAKEKEY001",
    # as an environment variable often holds it: newlines escaped
    "APPLE_MUSIC_PRIVATE_KEY": TEST_PRIVATE_KEY.replace("\n", "\\n"),
}
SWITCHED_ON = {**CREDENTIALS, "APPLE_MUSIC_PREVIEWS": "true"}
NO_RESULTS = {"results": {}}
NO_SONGS = {"data": []}


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


def response(status, data, headers=None):
    return SimpleNamespace(status_code=status, json=lambda: data, headers=headers or {})


def rate_limited(retry_after=None):
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else {}
    return response(429, fixture("rate_limited.json"), headers)


def artists(*found):
    """search results naming these (name, id) artists"""
    return {"results": {"artists": {"data": [{"id": i, "type": "artists", "attributes": {"name": n}} for n, i in found]}}}


def top_songs(song_id, album_id):
    url = f"https://music.apple.com/us/album/a-song/{album_id}?i={song_id}"
    return {"data": [{"id": song_id, "type": "songs", "attributes": {"name": "A Song", "url": url}}]}


class FakeAppleMusic:
    """
    searches answer from `results` (search term -> data, or a list of responses given in
    turn), and top-songs views from `songs` (artist id -> data, or a list); anything else
    finds nothing
    """

    def __init__(self, results=None, songs=None):
        self.results = dict(results or {})
        self.songs = dict(songs or {})
        self.requests = []
        self.sleeps = []
        self.now = 1_800_000_000.0

    def get(self, url, params=None, headers=None, timeout=None):
        self.requests.append(SimpleNamespace(url=url, params=params, headers=headers))
        if url.endswith("/search"):
            answer = self.results.get(params["term"], NO_RESULTS)
        else:
            artist_id = url.split("/artists/")[1].split("/")[0]
            answer = self.songs.get(artist_id, NO_SONGS)
        if isinstance(answer, list):
            return answer.pop(0)
        return answer if hasattr(answer, "status_code") else response(200, answer)

    @property
    def searches(self):
        return [r.params["term"] for r in self.requests if r.url.endswith("/search")]

    @property
    def song_lookups(self):
        return [r.url.split("/artists/")[1].split("/")[0] for r in self.requests if "/view/top-songs" in r.url]

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def client(self, team_id="FAKETEAM01", key_id="FAKEKEY001", private_key=TEST_PRIVATE_KEY):
        return AppleMusicClient(team_id, key_id, private_key, session=self, sleep=self.sleep, clock=self.clock)

    def patch(self, where="core.management.commands.match_apple_music_artists.AppleMusicClient"):
        """use this fake wherever `where` makes an AppleMusicClient"""
        return mock.patch(where, lambda *credentials: self.client(*credentials))
