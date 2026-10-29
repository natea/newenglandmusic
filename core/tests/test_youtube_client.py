from core.music_ids import MUSICBRAINZ_SECONDS_BETWEEN_REQUESTS
from core.tests.youtube_fixture import (
    DINOSAUR_CHANNEL,
    DINOSAUR_SPOTIFY,
    TEST_KEY,
    FakeWeb,
    fixture,
    quota_exceeded,
    response,
    video,
)
from core.music_ids import MusicBrainzBusy
from core.youtube import YouTubeError, YouTubeKeyRejected, YouTubeQuotaExceeded, parse_link, uploads_playlist
from unittest import mock

from core.user_agent import user_agent
from django.test import SimpleTestCase


class YouTubeClientTestCase(SimpleTestCase):
    def test_key_only_in_the_header(self):
        web = FakeWeb(searches={"The Ballroom Thieves Archers": ["arChErS0001"]})
        self.assertEqual(web.youtube().search_videos("The Ballroom Thieves Archers"), ["arChErS0001"])
        request = web.requests[0]
        self.assertEqual(request.headers, {"X-goog-api-key": TEST_KEY})
        self.assertNotIn(TEST_KEY, request.url)
        self.assertNotIn(TEST_KEY, str(request.params))
        self.assertEqual(request.params["type"], "video")
        self.assertEqual(request.params["maxResults"], 10)

    def test_key_out_of_errors(self):
        web = FakeWeb(searches={"x": response(400, fixture("bad_request.json"))})
        with self.assertRaises(YouTubeError) as raised:
            web.youtube().search_videos("x")
        self.assertNotIn(TEST_KEY, str(raised.exception))
        self.assertIn("badRequest", str(raised.exception))

    def test_quota_exceeded(self):
        web = FakeWeb(searches={"x": quota_exceeded()})
        with self.assertRaises(YouTubeQuotaExceeded):
            web.youtube().search_videos("x")
        self.assertEqual(len(web.requests), 1)

    def test_referrer_restricted_key_rejected(self):
        blocked = response(403, {"error": {"code": 403, "errors": [{"reason": "forbidden"}], "status": "PERMISSION_DENIED"}})
        web = FakeWeb(searches={"x": blocked})
        with self.assertRaises(YouTubeKeyRejected) as raised:
            web.youtube().search_videos("x")
        self.assertIn("application restriction", str(raised.exception))
        self.assertNotIn(TEST_KEY, str(raised.exception))

    def test_backs_off_then_succeeds(self):
        web = FakeWeb(searches={"x": [response(503, {}), response(429, {}), response(200, {"items": []})]})
        self.assertEqual(web.youtube().search_videos("x"), [])
        self.assertEqual(web.sleeps, [1, 2])

    def test_gives_up_after_three_tries(self):
        web = FakeWeb(searches={"x": [response(503, {}), response(503, {}), response(503, {})]})
        with self.assertRaises(YouTubeError):
            web.youtube().search_videos("x")
        self.assertEqual(len(web.requests), 3)

    def test_videos_and_channels(self):
        web = FakeWeb(
            videos={"arChErS0001": video("arChErS0001", "UCBallroomThievesTopic01", "The Ballroom Thieves - Topic", "Archers", embeddable=False)},
            channels={DINOSAUR_CHANNEL},
        )
        client = web.youtube()
        found = client.videos(["arChErS0001", "gone0000000"])
        self.assertEqual(list(found), ["arChErS0001"])
        self.assertEqual(found["arChErS0001"]["channel_title"], "The Ballroom Thieves - Topic")
        self.assertFalse(found["arChErS0001"]["embeddable"])
        self.assertEqual(client.channels([DINOSAUR_CHANNEL, "UCgone00000000000000000a"]), {DINOSAUR_CHANNEL})
        self.assertEqual(client.units, 2)

    def test_parse_link(self):
        self.assertEqual(parse_link("https://youtu.be/dQw4w9WgXcQ"), ("video", "dQw4w9WgXcQ"))
        self.assertEqual(parse_link("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3"), ("video", "dQw4w9WgXcQ"))
        self.assertEqual(parse_link(f"https://www.youtube.com/channel/{DINOSAUR_CHANNEL}"), ("channel", DINOSAUR_CHANNEL))
        self.assertIsNone(parse_link("https://open.spotify.com/artist/abc123"))
        self.assertIsNone(parse_link("https://www.youtube.com/@dinosaurjr"))
        self.assertEqual(uploads_playlist(DINOSAUR_CHANNEL), "UUfo74Lcf9bcQJd2MMq-XBzw")


class MusicIdsTestCase(SimpleTestCase):
    def test_wikidata_link(self):
        web = FakeWeb(wikidata={("P1902", DINOSAUR_SPOTIFY): [DINOSAUR_CHANNEL]})
        found = web.music_ids().wikidata_channels(spotify_ids=[DINOSAUR_SPOTIFY, "0" * 22], apple_ids=["12345"])
        self.assertEqual(found, {("spotify", DINOSAUR_SPOTIFY): {DINOSAUR_CHANNEL}})
        self.assertEqual([r.method for r in web.requests], ["POST", "POST"])

    def test_wikidata_skips_ids_that_arent_ids(self):
        web = FakeWeb()
        web.music_ids().wikidata_channels(spotify_ids=['x" } ?a ?b ?c {'], apple_ids=["abc"])
        self.assertEqual(web.requests, [])

    def test_musicbrainz_link(self):
        web = FakeWeb(musicbrainz={DINOSAUR_SPOTIFY: [f"https://www.youtube.com/channel/{DINOSAUR_CHANNEL}", "https://www.youtube.com/@dinosaurjr"]})
        self.assertEqual(web.music_ids().musicbrainz_channels(DINOSAUR_SPOTIFY), {DINOSAUR_CHANNEL})
        self.assertTrue(all("venue-db-event-check/1.0" in r.headers["User-Agent"] for r in web.requests))
        # musicbrainz asks for a way to reach us: API_CONTACT_EMAIL

    def test_contact_email_from_the_environment(self):
        web = FakeWeb(musicbrainz={DINOSAUR_SPOTIFY: []})
        with mock.patch.dict("os.environ", {"API_CONTACT_EMAIL": "someone@example.org"}):
            web.music_ids().musicbrainz_channels(DINOSAUR_SPOTIFY)
        self.assertTrue(all(r.headers["User-Agent"].endswith("; someone@example.org )") for r in web.requests))
        with mock.patch.dict("os.environ", {"API_CONTACT_EMAIL": ""}):
            self.assertEqual(user_agent(), "venue-db-event-check/1.0 ( https://newenglandmusic.onrender.com )")

    def test_musicbrainz_no_link(self):
        web = FakeWeb()
        self.assertEqual(web.music_ids().musicbrainz_channels(DINOSAUR_SPOTIFY), set())
        self.assertEqual(len(web.requests), 1)

    def test_musicbrainz_busy_then_answers(self):
        web = FakeWeb(musicbrainz={DINOSAUR_SPOTIFY: [f"https://www.youtube.com/channel/{DINOSAUR_CHANNEL}"]}, musicbrainz_503s=2)
        self.assertEqual(web.music_ids().musicbrainz_channels(DINOSAUR_SPOTIFY), {DINOSAUR_CHANNEL})
        self.assertEqual(web.sleeps[:2], [2, 4])

    def test_musicbrainz_stays_busy(self):
        web = FakeWeb(musicbrainz_503s=10)
        with self.assertRaises(MusicBrainzBusy):
            web.music_ids().musicbrainz_channels(DINOSAUR_SPOTIFY)
        # about two minutes of tries before giving up
        self.assertEqual(len(web.requests), 8)
        self.assertEqual(web.sleeps, [2, 4, 8, 15, 30, 30, 30])

    def test_musicbrainz_paced(self):
        web = FakeWeb(musicbrainz={DINOSAUR_SPOTIFY: []})
        ids = web.music_ids()
        ids.musicbrainz_channels(DINOSAUR_SPOTIFY)
        ids.musicbrainz_channels(DINOSAUR_SPOTIFY)
        self.assertEqual(len(web.requests), 4)
        self.assertEqual(len(web.sleeps), 3)
        self.assertTrue(all(abs(s - MUSICBRAINZ_SECONDS_BETWEEN_REQUESTS) < 1e-6 for s in web.sleeps))
