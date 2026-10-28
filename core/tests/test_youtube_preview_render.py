import datetime
from unittest import mock

from core.models import Event, YouTubeArtistLink
from core.tests.apple_music_fixture import SWITCHED_ON as APPLE_ON
from core.tests.spotify_fixture import CREDENTIALS as SPOTIFY_CREDENTIALS
from core.tests.test_apple_music_preview_render import apple_link, spotify_link
from core.tests.youtube_fixture import DINOSAUR_CHANNEL, SWITCHED_ON, TEST_KEY
from django.test import TestCase
from django.utils import timezone

VIDEO = "abc123DEF45"


def youtube_link(name_key, video_id="", channel_id="UCBallroomThievesTopic01", status=YouTubeArtistLink.Status.MATCHED):
    now = timezone.now()
    YouTubeArtistLink.objects.create(
        name_key=name_key, status=status, evidence=YouTubeArtistLink.Evidence.TOPIC_SONG,
        video_id=video_id, channel_id=channel_id, checked_at=now, last_seen_at=now,
    )


class YouTubePreviewRenderTestCase(TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict("os.environ", {**SWITCHED_ON, **APPLE_ON, **SPOTIFY_CREDENTIALS}))

    def event(self, **fields):
        event = Event.objects.create(starttime=timezone.now() + datetime.timedelta(days=1), **fields)
        return Event.objects.get(pk=event.pk).baked_html_template

    def test_youtube_button_beside_the_others(self):
        spotify_link("ballroom thieves", "fakeBallroomThieves01")
        apple_link("ballroom thieves", "489634654")
        youtube_link("ballroom thieves", VIDEO)
        html = self.event(artists="The Ballroom Thieves")
        row = html[html.index('<div class="artist-previews">'):]
        spotify, apple, youtube = row.index('class="spotify-play"'), row.index('class="apple-play"'), row.index('class="youtube-play"')
        self.assertLess(spotify, apple)
        self.assertLess(apple, youtube)
        self.assertIn(f'href="https://www.youtube.com/watch?v={VIDEO}"', row)
        self.assertIn('data-artist-name="The Ballroom Thieves"', row)

    def test_channel_only_match_links_to_the_channel(self):
        youtube_link("dinosaur jr", channel_id=DINOSAUR_CHANNEL)
        html = self.event(artists="Dinosaur Jr.")
        self.assertIn(f'href="https://www.youtube.com/channel/{DINOSAUR_CHANNEL}"', html)
        self.assertIn('data-youtube-video=""', html)

    def test_no_player_or_script_before_a_click(self):
        youtube_link("ballroom thieves", VIDEO)
        self.event(artists="The Ballroom Thieves")
        page = self.client.get("/").content.decode()
        self.assertIn("youtube-play", page)
        self.assertNotIn("<iframe", page)
        self.assertNotIn("youtube-nocookie.com", page)
        self.assertNotIn("youtube.com/iframe_api", page)
        self.assertNotIn(TEST_KEY, page)

    def test_unmatched_names_get_no_button(self):
        youtube_link("ballroom thieves", VIDEO, status=YouTubeArtistLink.Status.NOT_FOUND)
        self.assertNotIn("youtube-play", self.event(artists="The Ballroom Thieves"))

    def test_switched_off(self):
        youtube_link("ballroom thieves", VIDEO)
        with mock.patch.dict("os.environ", {"YOUTUBE_PREVIEWS": "false"}):
            self.assertNotIn("youtube-play", self.event(artists="The Ballroom Thieves"))
