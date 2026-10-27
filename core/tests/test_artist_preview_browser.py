"""
the spotify and apple music play buttons in a real browser (playwright's headless chromium),
for what only javascript does: opening, swapping and closing the players. every request that
isn't to the test server is aborted, so the suite stays offline -- neither service's player
actually loads; the tests check the iframes' src instead.

needs `python -m playwright install chromium` once (ci does it).
"""

import datetime
from unittest import mock

from core.models import AppleMusicArtistLink, Event, SpotifyArtistLink
from core.tests.apple_music_fixture import SWITCHED_ON
from core.tests.spotify_fixture import CREDENTIALS
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils import timezone
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


def matched(name_key, artist_id):
    now = timezone.now()
    SpotifyArtistLink.objects.create(
        name_key=name_key, status=SpotifyArtistLink.Status.MATCHED, spotify_artist_id=artist_id,
        checked_at=now, last_seen_at=now,
    )


def apple_matched(name_key, artist_id, song_id, album_id):
    now = timezone.now()
    AppleMusicArtistLink.objects.create(
        name_key=name_key, status=AppleMusicArtistLink.Status.MATCHED, apple_artist_id=artist_id,
        top_song_id=song_id, top_album_id=album_id, checked_at=now, last_seen_at=now,
    )


class PreviewBrowserTestCase(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        # playwright's sync api runs an event loop, which django's orm refuses without this
        cls.async_unsafe = mock.patch.dict("os.environ", {"DJANGO_ALLOW_ASYNC_UNSAFE": "true"})
        cls.async_unsafe.start()
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch()
        except PlaywrightError as e:
            cls.playwright.stop()
            super().tearDownClass()
            cls.async_unsafe.stop()
            # fail, not skip: a skipped test isn't a passing one
            raise AssertionError(
                f"chromium isn't installed for playwright: run `python -m playwright install chromium` ({e})"
            )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()
        cls.async_unsafe.stop()

    def setUp(self):
        self.enterContext(mock.patch.dict("os.environ", {**CREDENTIALS, **SWITCHED_ON}))
        matched("psymon spine", "fakePsymonSpine")
        apple_matched("psymon spine", "100000051", "964625539", "964625535")
        matched("lake street dive", "fakeLSD")
        tomorrow = timezone.now() + datetime.timedelta(days=1)
        Event.objects.create(artists="SHEBAD, Psymon Spine", starttime=tomorrow)
        Event.objects.create(artists="Lake Street Dive", starttime=tomorrow + datetime.timedelta(hours=1))
        self.blocked = []

    def open_homepage(self, javascript=True):
        context = self.browser.new_context(java_script_enabled=javascript)
        self.addCleanup(context.close)
        context.route("**/*", self.only_the_test_server)
        page = context.new_page()
        page.goto(self.live_server_url + "/")
        return context, page

    def only_the_test_server(self, route):
        if route.request.url.startswith(self.live_server_url):
            route.continue_()
        else:
            self.blocked.append(route.request.url)
            route.abort()

    def players(self, page):
        return page.locator("iframe.spotify-player")

    def test_no_player_before_a_click(self):
        _, page = self.open_homepage()
        self.assertEqual(self.players(page).count(), 0)
        self.assertFalse([url for url in self.blocked if "spotify.com" in url])

    def test_click_opens_the_player_below_the_buttons(self):
        _, page = self.open_homepage()
        page.click("a.spotify-play[data-spotify-artist=fakePsymonSpine]")
        player = self.players(page)
        self.assertEqual(player.count(), 1)
        self.assertEqual(player.get_attribute("src"), "https://open.spotify.com/embed/artist/fakePsymonSpine")
        # right after the row of buttons, inside the event
        self.assertTrue(
            page.evaluate(
                "() => document.querySelector('iframe.spotify-player').previousElementSibling"
                ".classList.contains('artist-previews')"
            )
        )
        self.assertEqual(page.url, self.live_server_url + "/")

    def test_one_player_at_a_time(self):
        _, page = self.open_homepage()
        page.click("a.spotify-play[data-spotify-artist=fakePsymonSpine]")
        page.click("a.spotify-play[data-spotify-artist=fakeLSD]")
        self.assertEqual(self.players(page).count(), 1)
        self.assertEqual(
            self.players(page).get_attribute("src"), "https://open.spotify.com/embed/artist/fakeLSD"
        )

    def test_second_click_closes_the_player(self):
        _, page = self.open_homepage()
        button = "a.spotify-play[data-spotify-artist=fakePsymonSpine]"
        page.click(button)
        page.click(button)
        self.assertEqual(self.players(page).count(), 0)

    def test_without_javascript_the_button_is_a_link_to_spotify(self):
        context, page = self.open_homepage(javascript=False)
        with context.expect_page() as new_tab:
            page.click("a.spotify-play[data-spotify-artist=fakePsymonSpine]")
        new_tab.value.wait_for_load_state("commit")
        self.assertIn("https://open.spotify.com/artist/fakePsymonSpine", self.blocked)
        self.assertEqual(self.players(page).count(), 0)

    def apple_players(self, page):
        return page.locator(".apple-player iframe")

    def test_apple_click_opens_the_top_song_and_the_artist_link(self):
        _, page = self.open_homepage()
        page.click("a.apple-play[data-apple-artist='100000051']")
        self.assertEqual(self.apple_players(page).count(), 1)
        self.assertEqual(
            self.apple_players(page).get_attribute("src"),
            "https://embed.music.apple.com/us/album/964625535?i=964625539",
        )
        more = page.locator(".apple-player a.apple-more")
        self.assertEqual(more.inner_text(), "More by Psymon Spine on Apple Music")
        self.assertEqual(more.get_attribute("href"), "https://music.apple.com/us/artist/100000051")
        # right after the row of buttons
        self.assertTrue(
            page.evaluate(
                "() => document.querySelector('.apple-player').previousElementSibling"
                ".classList.contains('artist-previews')"
            )
        )

    def test_one_player_across_services(self):
        _, page = self.open_homepage()
        page.click("a.spotify-play[data-spotify-artist=fakePsymonSpine]")
        self.assertEqual(self.players(page).count(), 1)
        page.click("a.apple-play[data-apple-artist='100000051']")
        self.assertEqual(self.players(page).count(), 0)
        self.assertEqual(self.apple_players(page).count(), 1)
        page.click("a.spotify-play[data-spotify-artist=fakeLSD]")
        self.assertEqual(self.apple_players(page).count(), 0)
        self.assertEqual(self.players(page).count(), 1)

    def test_second_apple_click_closes_it(self):
        _, page = self.open_homepage()
        button = "a.apple-play[data-apple-artist='100000051']"
        page.click(button)
        page.click(button)
        self.assertEqual(page.locator(".apple-player").count(), 0)

    def test_no_apple_player_before_a_click(self):
        _, page = self.open_homepage()
        self.assertEqual(page.locator(".apple-player").count(), 0)
        self.assertFalse([url for url in self.blocked if "apple.com" in url])
