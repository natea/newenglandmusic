"""
the discovery deck in a real browser (playwright's headless chromium), for what only
javascript does. every request that isn't to the test server is aborted and remembered in
self.blocked, so nothing really loads from any service.

see core/tests/browser.py.
"""

import os
from unittest import mock

from core.models import Band
from core.tests.apple_music_fixture import SWITCHED_ON as APPLE_ON
from core.tests.browser import BrowserTestCase
from core.tests.discover_fixture import apple, days, show, spotify, venue, youtube
from core.tests.spotify_fixture import CREDENTIALS as SPOTIFY_ON
from core.tests.youtube_fixture import SWITCHED_ON as YOUTUBE_ON


class DiscoverBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch.dict(os.environ, {**SPOTIFY_ON, **APPLE_ON, **YOUTUBE_ON}))
        self.lupo = venue()

    def make_act(self, name, services=("youtube", "apple", "spotify"), shows=1):
        band = Band.objects.create(name=name, city_town="Providence", state="RI")
        key = name.lower()
        for service in services:
            {"youtube": youtube, "apple": apple, "spotify": spotify}[service](key)
        events = [show(band, days(3 + n), self.lupo) for n in range(shows)]
        return band, events

    def requests_to(self, *hosts):
        return [url for url in self.blocked if any(host in url for host in hosts)]


class PlayersAreNotRequestedUntilClickedTestCase(DiscoverBrowserTestCase):
    def test_no_request_to_apple_music_or_youtube_before_a_play_button_is_clicked(self):
        self.make_act("Belly", services=("youtube", "apple"))
        _, page = self.open_page("/discover")
        self.assertEqual(page.locator("a.youtube-play").count(), 1)
        self.assertEqual(page.locator("a.apple-play").count(), 1)
        self.assertEqual(self.requests_to("apple.com", "youtube"), [])
