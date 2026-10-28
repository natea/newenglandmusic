"""
the youtube play buttons in a real browser, for what only javascript does: opening, swapping
and closing the player. every request that isn't to the test server is aborted
(core/tests/browser.py), so nothing is fetched from youtube; the tests check the iframe.
"""

import datetime
from unittest import mock

from core.models import Event, YouTubeArtistLink
from core.tests.apple_music_fixture import SWITCHED_ON as APPLE_ON
from core.tests.browser import BrowserTestCase
from core.tests.test_artist_preview_browser import apple_matched
from core.tests.youtube_fixture import DINOSAUR_CHANNEL, SWITCHED_ON
from django.utils import timezone

VIDEO = "abc123DEF45"


def youtube_matched(name_key, video_id="", channel_id="UCBallroomThievesTopic01"):
    now = timezone.now()
    YouTubeArtistLink.objects.create(
        name_key=name_key, status=YouTubeArtistLink.Status.MATCHED, evidence=YouTubeArtistLink.Evidence.TOPIC_SONG,
        video_id=video_id, channel_id=channel_id, checked_at=now, last_seen_at=now,
    )


class YouTubePreviewBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch.dict("os.environ", {**APPLE_ON, **SWITCHED_ON}))
        youtube_matched("ballroom thieves", VIDEO)
        apple_matched("ballroom thieves", "489634654", "964625539", "964625535")
        youtube_matched("dinosaur jr", channel_id=DINOSAUR_CHANNEL)
        tomorrow = timezone.now() + datetime.timedelta(days=1)
        Event.objects.create(artists="The Ballroom Thieves", starttime=tomorrow)
        Event.objects.create(artists="Dinosaur Jr.", starttime=tomorrow + datetime.timedelta(hours=1))

    def player(self, page):
        return page.locator(".youtube-player iframe")

    def test_no_player_before_a_click(self):
        _, page = self.open_page("/")
        self.assertEqual(page.locator("iframe").count(), 0)
        self.assertFalse([url for url in self.blocked if "youtube" in url])

    def test_click_opens_the_video(self):
        _, page = self.open_page("/")
        page.click(f"a.youtube-play[data-youtube-video={VIDEO}]")
        player = self.player(page)
        self.assertEqual(player.count(), 1)
        self.assertEqual(player.get_attribute("src"), f"https://www.youtube-nocookie.com/embed/{VIDEO}")
        box = player.bounding_box()
        self.assertGreaterEqual(box["width"], 200)
        self.assertGreaterEqual(box["height"], 200)
        more = page.locator(".youtube-more")
        self.assertEqual(more.inner_text(), "More by The Ballroom Thieves on YouTube")
        self.assertEqual(more.get_attribute("href"), "https://www.youtube.com/channel/UCBallroomThievesTopic01")
        # nothing drawn over it, and no autoplay asked for
        self.assertNotIn("autoplay", player.get_attribute("src"))
        self.assertNotIn("autoplay", player.get_attribute("allow"))
        center = (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        self.assertTrue(page.evaluate("([x, y]) => document.elementFromPoint(x, y).tagName === 'IFRAME'", list(center)))

    def test_channel_only_match_plays_its_uploads(self):
        _, page = self.open_page("/")
        page.click(f"a.youtube-play[data-youtube-channel={DINOSAUR_CHANNEL}]")
        self.assertEqual(
            self.player(page).get_attribute("src"),
            "https://www.youtube-nocookie.com/embed/videoseries?list=UUfo74Lcf9bcQJd2MMq-XBzw",
        )

    def test_one_player_across_services(self):
        _, page = self.open_page("/")
        page.click("a.apple-play[data-apple-song='964625539']")
        self.assertEqual(page.locator(".apple-player").count(), 1)
        page.click(f"a.youtube-play[data-youtube-video={VIDEO}]")
        self.assertEqual(page.locator(".apple-player").count(), 0)
        self.assertEqual(self.player(page).count(), 1)

    def test_second_click_removes_it(self):
        _, page = self.open_page("/")
        button = f"a.youtube-play[data-youtube-video={VIDEO}]"
        page.click(button)
        page.click(button)
        self.assertEqual(page.locator(".youtube-player").count(), 0)

    def test_without_javascript_its_a_link(self):
        _, page = self.open_page("/", javascript=False)
        self.assertEqual(
            page.locator(f"a.youtube-play[data-youtube-video={VIDEO}]").get_attribute("href"),
            f"https://www.youtube.com/watch?v={VIDEO}",
        )
