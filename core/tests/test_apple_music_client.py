from unittest import mock

import jwt
from core.apple_music import (
    AppleMusicAuthError,
    AppleMusicBlocked,
    AppleMusicBusy,
    AppleMusicError,
    credentials,
    parse_artist_id,
    previews_enabled,
)
from core.tests.apple_music_fixture import (
    CREDENTIALS,
    SWITCHED_ON,
    TEST_PRIVATE_KEY,
    TEST_PUBLIC_KEY,
    FakeAppleMusic,
    fixture,
    rate_limited,
    response,
)
from django.test import SimpleTestCase


def bearer(request):
    return request.headers["Authorization"].removeprefix("Bearer ")


class DeveloperTokenTestCase(SimpleTestCase):
    def test_token_signed_correctly(self):
        apple = FakeAppleMusic()
        apple.client().search_artists("Epicenter")
        token = bearer(apple.requests[0])
        self.assertEqual(jwt.get_unverified_header(token), {"alg": "ES256", "kid": "FAKEKEY001", "typ": "JWT"})
        claims = jwt.decode(token, TEST_PUBLIC_KEY, algorithms=["ES256"], options={"verify_exp": False, "verify_iat": False})  # the fake clock is in 2027
        self.assertEqual(claims["iss"], "FAKETEAM01")
        self.assertLessEqual(claims["exp"] - claims["iat"], 3600)
        # backdated a minute, for servers whose clocks are a little behind
        self.assertEqual(claims["iat"], int(apple.now) - 60)

    def test_token_reused_until_near_expiry(self):
        apple = FakeAppleMusic()
        client = apple.client()
        client.search_artists("One")
        client.search_artists("Two")
        self.assertEqual(bearer(apple.requests[0]), bearer(apple.requests[1]))
        apple.now += 3400
        client.search_artists("Three")
        self.assertNotEqual(bearer(apple.requests[0]), bearer(apple.requests[2]))

    def test_escaped_newlines_in_the_environment_restored(self):
        with mock.patch.dict("os.environ", CREDENTIALS):
            team_id, key_id, private_key = credentials()
        self.assertEqual((team_id, key_id, private_key), ("FAKETEAM01", "FAKEKEY001", TEST_PRIVATE_KEY))

    def test_not_configured(self):
        with mock.patch.dict("os.environ", {"APPLE_MUSIC_PRIVATE_KEY": ""}):
            self.assertIsNone(credentials())

    def test_previews_need_credentials_and_the_switch(self):
        with mock.patch.dict("os.environ", CREDENTIALS):
            self.assertFalse(previews_enabled())
        with mock.patch.dict("os.environ", SWITCHED_ON):
            self.assertTrue(previews_enabled())
        with mock.patch.dict("os.environ", {**SWITCHED_ON, "APPLE_MUSIC_KEY_ID": ""}):
            self.assertFalse(previews_enabled())


class RequestsTestCase(SimpleTestCase):
    def test_search(self):
        apple = FakeAppleMusic({"The Ballroom Thieves": fixture("search_unique.json")})
        found = apple.client().search_artists("The Ballroom Thieves")
        self.assertEqual(found[0], {"id": "489634654", "name": "The Ballroom Thieves"})
        self.assertTrue(apple.requests[0].url.endswith("/v1/catalog/us/search"))
        self.assertEqual(apple.requests[0].params, {"term": "The Ballroom Thieves", "types": "artists", "limit": 10})

    def test_search_with_no_artists(self):
        apple = FakeAppleMusic({"Nobody": fixture("search_empty.json")})
        self.assertEqual(apple.client().search_artists("Nobody"), [])

    def test_top_song_and_its_album_from_the_song_url(self):
        apple = FakeAppleMusic(songs={"489634654": fixture("top_songs.json")})
        self.assertEqual(apple.client().top_song("489634654"), {"song_id": "964625539", "album_id": "964625535"})
        self.assertTrue(apple.requests[0].url.endswith("/v1/catalog/us/artists/489634654/view/top-songs"))
        self.assertEqual(apple.requests[0].params, {"limit": 1})

    def test_no_top_songs(self):
        apple = FakeAppleMusic(songs={"100000099": fixture("top_songs_empty.json")})
        self.assertIsNone(apple.client().top_song("100000099"))

    def test_requests_spaced_apart(self):
        apple = FakeAppleMusic()
        client = apple.client()
        client.search_artists("One")
        client.search_artists("Two")
        self.assertEqual(apple.sleeps, [0.5])

    def test_retry_after_then_success(self):
        apple = FakeAppleMusic({"One": [rate_limited(3), response(200, fixture("search_unique.json"))]})
        self.assertEqual(len(apple.client().search_artists("One")), 2)
        self.assertIn(3.0, apple.sleeps)

    def test_three_429s_raise_busy(self):
        apple = FakeAppleMusic({"One": [rate_limited(), rate_limited(), rate_limited()]})
        with self.assertRaises(AppleMusicBusy):
            apple.client().search_artists("One")
        self.assertEqual(len(apple.requests), 3)
        self.assertIn(1, apple.sleeps)
        self.assertIn(2, apple.sleeps)

    def test_long_retry_after_raises_blocked_without_waiting(self):
        apple = FakeAppleMusic({"One": [rate_limited(86400)]})
        with self.assertRaises(AppleMusicBlocked):
            apple.client().search_artists("One")
        self.assertEqual(apple.sleeps, [])

    def test_spurious_401s_retried_with_the_same_token(self):
        rejected = response(401, fixture("unauthorized.json"))
        apple = FakeAppleMusic({"One": [rejected] * 4 + [response(200, fixture("search_unique.json"))]})
        apple.client().search_artists("One")
        self.assertEqual(len(apple.requests), 5)
        self.assertEqual([s for s in apple.sleeps if s >= 1], [2, 4, 8, 16])
        self.assertEqual(len({bearer(request) for request in apple.requests}), 1)

    def test_401_raises_auth_error_without_secrets(self):
        apple = FakeAppleMusic({"One": [response(401, fixture("unauthorized.json"))] * 5})
        client = apple.client()
        with self.assertRaises(AppleMusicAuthError) as raised:
            client.search_artists("One")
        message = str(raised.exception)
        self.assertIn("APPLE_MUSIC_KEY_ID", message)
        self.assertNotIn(client.token, message)
        self.assertNotIn("PRIVATE KEY", message)

    def test_other_errors_carry_apples_detail_without_secrets(self):
        error = {"errors": [{"status": "500", "title": "Server Error", "detail": "Something broke"}]}
        apple = FakeAppleMusic({"One": [response(500, error)]})
        client = apple.client()
        with self.assertRaises(AppleMusicError) as raised:
            client.search_artists("One")
        self.assertIn("Something broke", str(raised.exception))
        self.assertNotIn(client.token, str(raised.exception))


class ParseArtistIdTestCase(SimpleTestCase):
    def test_artist_urls(self):
        self.assertEqual(parse_artist_id("https://music.apple.com/us/artist/the-ballroom-thieves/489634654"), "489634654")
        self.assertEqual(parse_artist_id("https://music.apple.com/gb/artist/489634654?l=en"), "489634654")

    def test_other_links_rejected(self):
        for text in (
            "https://open.spotify.com/artist/abc123",
            "https://music.apple.com/us/album/archers/964625535?i=964625539",
            "not a link",
        ):
            self.assertIsNone(parse_artist_id(text), text)
