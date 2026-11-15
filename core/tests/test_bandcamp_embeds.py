from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import requests
from django.test import SimpleTestCase

from core import bandcamp_embeds
from core.bandcamp_embeds import Result, find_candidates, lookup

FIXTURES = Path(__file__).parent / "fixtures" / "bandcamp"
FRONT = "https://krill.bandcamp.com/"
ROBOTS = "https://krill.bandcamp.com/robots.txt"


def page(name):
    return (FIXTURES / name).read_text()


def player(kind, embed_id):
    return f"https://bandcamp.com/EmbeddedPlayer/{kind}={embed_id}/size=large/tracklist=true/artwork=small/"


def reply(url, status=200, text="", location=None):
    return SimpleNamespace(status_code=status, text=text, url=url, headers={"Location": location} if location else {})


class FakeSession:
    """answers get() from a dict of url -> text, response or exception; a missing url is a 404"""

    def __init__(self, pages):
        self.pages = pages
        self.requested = []
        self.headers = {}
        self.trust_env = True

    def get(self, url, timeout=None, allow_redirects=True):
        self.requested.append(url)
        answer = self.pages.get(url)
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            return reply(url, 404)
        return reply(url, 200, answer) if isinstance(answer, str) else answer

    def pages_requested(self):
        return [url for url in self.requested if not url.endswith("/robots.txt")]


def looked_up(pages):
    session = FakeSession(pages)
    return lookup(session, FRONT), session


class CandidatesTestCase(SimpleTestCase):
    def test_an_album_by_its_json_ld(self):
        self.assertEqual(find_candidates(page("album_redirect.html")), [("album", "111")])

    def test_a_track_by_its_page_properties(self):
        self.assertEqual(find_candidates(page("track_page.html")), [("track", "222")])

    def test_music_tiles_in_page_order(self):
        self.assertEqual(
            find_candidates(page("grid.html")),
            [("album", "333"), ("track", "334"), ("album", "335"), ("album", "336")],
        )

    def test_merchandise_tiles_are_skipped(self):
        self.assertEqual(find_candidates(page("merch_grid.html")), [])
        self.assertEqual(find_candidates(page("music_page.html")), [("track", "444")])

    def test_a_page_with_nothing(self):
        self.assertEqual(find_candidates(page("empty.html")), [])
        self.assertEqual(find_candidates("<ld>"), [])

    def test_broken_json_is_ignored(self):
        html = '<script type="application/ld+json">{oops</script><meta name="bc-page-properties" content="{no">'
        self.assertEqual(find_candidates(html), [])


class LookupTestCase(SimpleTestCase):
    def test_redirect_to_a_featured_album(self):
        result, session = looked_up({FRONT: page("album_redirect.html"), player("album", "111"): page("player_available.html")})
        self.assertEqual(result, Result("found", "album", "111"))
        self.assertEqual(session.pages_requested(), [FRONT, player("album", "111")])

    def test_redirect_to_a_track(self):
        result, _ = looked_up({FRONT: page("track_page.html"), player("track", "222"): page("player_available.html")})
        self.assertEqual(result, Result("found", "track", "222"))

    def test_discography_grid(self):
        result, _ = looked_up({FRONT: page("grid.html"), player("album", "333"): page("player_available.html")})
        self.assertEqual(result, Result("found", "album", "333"))

    def test_merchandise_first(self):
        result, session = looked_up(
            {
                FRONT: page("merch_grid.html"),
                "https://krill.bandcamp.com/music": page("music_page.html"),
                player("track", "444"): page("player_available.html"),
            }
        )
        self.assertEqual(result, Result("found", "track", "444"))
        self.assertEqual(session.pages_requested(), [FRONT, "https://krill.bandcamp.com/music", player("track", "444")])

    def test_physical_only_first_release(self):
        grid = page("grid.html").replace("album-333", "album-555").replace("track-334", "album-556")
        result, session = looked_up(
            {FRONT: grid, player("album", "555"): page("player_unavailable.html"), player("album", "556"): page("player_available.html")}
        )
        self.assertEqual(result, Result("found", "album", "556"))
        self.assertEqual(len(session.pages_requested()), 3)

    def test_nothing_playable(self):
        unavailable = page("player_unavailable.html")
        result, session = looked_up(
            {FRONT: page("grid.html"), **{player(k, i): unavailable for k, i in find_candidates(page("grid.html"))}}
        )
        self.assertEqual(result.status, "no_playable")
        self.assertEqual(result.embed_id, "")
        # the page and three players, never the fourth release
        self.assertEqual(len(session.pages_requested()), 4)
        self.assertNotIn(player("album", "336"), session.requested)

    def test_a_removed_release_is_skipped(self):
        result, _ = looked_up({FRONT: page("grid.html"), player("album", "333"): reply("", 404), player("track", "334"): page("player_available.html")})
        self.assertEqual(result, Result("found", "track", "334"))

    def test_a_page_with_no_release(self):
        result, session = looked_up({FRONT: page("empty.html"), "https://krill.bandcamp.com/music": page("empty.html")})
        self.assertEqual(result.status, "unreadable")
        self.assertEqual(session.pages_requested(), [FRONT, "https://krill.bandcamp.com/music"])

    def test_a_page_with_no_music_page_either(self):
        result, _ = looked_up({FRONT: page("empty.html")})
        self.assertEqual(result.status, "unreadable")

    def test_refused_by_robots(self):
        result, session = looked_up({ROBOTS: "User-agent: *\nDisallow: /\n"})
        self.assertEqual(result.status, "blocked")
        self.assertEqual(session.pages_requested(), [])

    def test_statuses(self):
        for code, status in ((404, "gone"), (410, "gone"), (403, "blocked"), (406, "blocked"), (429, "blocked"), (500, "failed")):
            result, _ = looked_up({FRONT: reply(FRONT, code)})
            self.assertEqual(result.status, status, code)
        result, _ = looked_up({FRONT: requests.Timeout()})
        self.assertEqual(result.status, "failed")

    def test_a_redirect_within_bandcamp_is_followed(self):
        album = "https://krill.bandcamp.com/album/salt"
        result, _ = looked_up(
            {FRONT: reply(FRONT, 302, location="/album/salt"), album: page("album_redirect.html"), player("album", "111"): page("player_available.html")}
        )
        self.assertEqual(result.embed_id, "111")

    def test_a_redirect_off_bandcamp_is_refused(self):
        result, session = looked_up({FRONT: reply(FRONT, 301, location="https://example.com/krill")})
        self.assertEqual(result.status, "failed")
        self.assertEqual(session.pages_requested(), [FRONT])

    def test_a_player_page_that_fails(self):
        result, _ = looked_up({FRONT: page("grid.html"), player("album", "333"): reply("", 429)})
        self.assertEqual(result.status, "blocked")


class PoliteSessionTestCase(SimpleTestCase):
    def test_two_seconds_apart_and_robots_asked_once(self):
        fake = FakeSession({FRONT: "x", "https://krill.bandcamp.com/music": "x"})
        sleeps, now = [], [0.0]
        with mock.patch.object(bandcamp_embeds.requests, "Session", return_value=fake):
            polite = bandcamp_embeds.PoliteSession("agent", sleep=sleeps.append, clock=lambda: now[0])
        polite.get(FRONT)
        polite.get(ROBOTS)
        polite.get(ROBOTS)
        polite.get("https://krill.bandcamp.com/music")
        self.assertEqual(sleeps, [2, 2])
        self.assertFalse(fake.trust_env)
        self.assertEqual(fake.headers["User-Agent"], "agent")
        self.assertEqual(fake.requested.count(ROBOTS), 1)
