import datetime
from unittest import mock

from core.models import AppleMusicArtistLink, Event, SpotifyArtistLink
from core.tests.apple_music_fixture import CREDENTIALS, SWITCHED_ON, TEST_PRIVATE_KEY, FakeAppleMusic
from core.tests.spotify_fixture import CREDENTIALS as SPOTIFY_CREDENTIALS
from django.test import TestCase
from django.utils import timezone


def apple_link(name_key, artist_id, song_id="964625539", album_id="964625535", **fields):
    now = timezone.now()
    AppleMusicArtistLink.objects.create(
        name_key=name_key, status=AppleMusicArtistLink.Status.MATCHED, apple_artist_id=artist_id,
        top_song_id=song_id, top_album_id=album_id, checked_at=now, last_seen_at=now, **fields,
    )


def spotify_link(name_key, artist_id):
    now = timezone.now()
    SpotifyArtistLink.objects.create(
        name_key=name_key, status=SpotifyArtistLink.Status.MATCHED, spotify_artist_id=artist_id,
        checked_at=now, last_seen_at=now,
    )


class ApplePreviewRenderTestCase(TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict("os.environ", {**SWITCHED_ON, **SPOTIFY_CREDENTIALS}))
        apple_link("ballroom thieves", "489634654")
        spotify_link("ballroom thieves", "fakeBallroomThieves01")

    def event(self, **fields):
        event = Event.objects.create(starttime=timezone.now() + datetime.timedelta(days=1), **fields)
        return Event.objects.get(pk=event.pk).baked_html_template

    def test_apple_button_beside_the_spotify_button(self):
        html = self.event(artists="The Ballroom Thieves")
        row = html[html.index('<div class="artist-previews">'):]
        spotify, apple = row.index('class="spotify-play"'), row.index('class="apple-play"')
        self.assertLess(spotify, apple)
        self.assertIn('href="https://music.apple.com/us/artist/489634654"', row)
        self.assertIn('data-apple-song="964625539" data-apple-album="964625535"', row)
        self.assertIn('data-artist-name="The Ballroom Thieves"', row)
        # one row, below the text, for both
        self.assertEqual(html.count('<div class="artist-previews">'), 1)

    def test_apple_only(self):
        apple_link("lake street dive", "100000041", song_id="200000041", album_id="300000041")
        html = self.event(artists="Lake Street Dive")
        self.assertIn('data-apple-artist="100000041"', html)
        self.assertNotIn("spotify-play", html)

    def test_no_button_without_a_top_song(self):
        apple_link("quiet band", "100000099", song_id="", album_id="")
        self.assertNotIn("apple-play", self.event(artists="Quiet Band"))

    def test_no_player_before_a_click(self):
        self.event(artists="The Ballroom Thieves")
        response = self.client.get("/")
        self.assertContains(response, 'class="apple-play"')
        self.assertNotContains(response, "embed.music.apple.com")
        self.assertNotContains(response, "<iframe")

    def test_switched_off(self):
        with mock.patch.dict("os.environ", {"APPLE_MUSIC_PREVIEWS": "false"}):
            html = self.event(artists="The Ballroom Thieves")
        self.assertNotIn("apple-play", html)
        self.assertIn("spotify-play", html)

    def test_not_configured(self):
        with mock.patch.dict("os.environ", {"APPLE_MUSIC_PRIVATE_KEY": ""}):
            self.assertNotIn("apple-play", self.event(artists="The Ballroom Thieves"))

    def test_secrets_stay_out_of_pages(self):
        self.event(artists="The Ballroom Thieves")
        token = FakeAppleMusic().client().developer_token()
        html = self.client.get("/").content.decode()
        self.assertIn("apple-play", html)
        for secret in (token, TEST_PRIVATE_KEY.splitlines()[1], CREDENTIALS["APPLE_MUSIC_PRIVATE_KEY"][:60]):
            self.assertNotIn(secret, html)
