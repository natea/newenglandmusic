"""
the spotify play buttons in a real browser (playwright's headless chromium), for what only
javascript does: opening, swapping and closing the player. every request that isn't to the
test server is aborted, so the suite stays offline -- spotify's player never actually loads;
the tests check the iframe's src instead.

needs `python -m playwright install chromium` once (ci does it).
"""

import datetime
from unittest import mock

from core.models import Event, SpotifyArtistLink
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
        self.enterContext(mock.patch.dict("os.environ", CREDENTIALS))
        matched("psymon spine", "fakePsymonSpine")
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
                ".classList.contains('spotify-artists')"
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
