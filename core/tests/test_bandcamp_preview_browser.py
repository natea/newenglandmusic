"""
the Bandcamp buttons in a real browser, for what only javascript does: opening, closing and
fitting the player. every request that isn't to the test server is aborted
(core/tests/browser.py), so nothing is fetched from Bandcamp; the tests check the iframe.
"""

import datetime
import os
from unittest import mock

from django.utils import timezone

from core.models import Band, Event, EventPerformer
from core.tests.browser import BrowserTestCase
from core.tests.test_bandcamp_preview_render import SERVICE_SETTINGS
from core.tests.new_england_fixture import new_england_venue

KRILL = "https://krill.bandcamp.com/"
PILE = "https://pile.bandcamp.com/"
BUTTON = "a.bandcamp-play[data-bandcamp-id='111']"
FRAME = ".bandcamp-player iframe"


class BandcampBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch.dict(os.environ, {name: "" for name in SERVICE_SETTINGS}))
        self.krill = self.make_band("Krill", KRILL, "111")
        self.pile = self.make_band("Pile", PILE, "222")
        tomorrow = timezone.now() + datetime.timedelta(days=1)
        self.make_event("Krill", self.krill, tomorrow)
        self.make_event("Pile", self.pile, tomorrow + datetime.timedelta(hours=1))

    def make_band(self, name, url, embed_id):
        return Band.objects.create(
            name=name, bandcamp_url=url, bandcamp_embed_kind="album", bandcamp_embed_id=embed_id,
            bandcamp_embed_status="found", bandcamp_embed_for=url,
        )

    def make_event(self, artists, band, starttime):
        event = Event.objects.create(artists=artists, venue=new_england_venue(), starttime=starttime)
        EventPerformer.objects.create(event=event, band=band)
        event.save()

    def test_nothing_loads_before_a_click(self):
        _, page = self.open_page("/")
        self.assertEqual(page.locator("iframe").count(), 0)
        self.assertFalse([url for url in self.blocked if "bandcamp.com/EmbeddedPlayer" in url])

    def test_pressing_the_event_button(self):
        _, page = self.open_page("/")
        page.click(BUTTON)
        frame = page.locator(FRAME)
        self.assertEqual(frame.count(), 1)
        self.assertEqual(
            frame.get_attribute("src"),
            "https://bandcamp.com/EmbeddedPlayer/album=111/size=large/tracklist=true/artwork=small/",
        )
        # right after the row of buttons, and bandcamp is asked only now
        self.assertTrue(
            page.evaluate("() => document.querySelector('.bandcamp-player').previousElementSibling.classList.contains('artist-previews')")
        )
        self.assertTrue([url for url in self.blocked if "bandcamp.com/EmbeddedPlayer/album=111" in url])
        # another act's player closes the first
        page.click("a.bandcamp-play[data-bandcamp-id='222']")
        self.assertEqual(page.locator(FRAME).count(), 1)
        self.assertIn("album=222", page.locator(FRAME).get_attribute("src"))
        self.assertEqual(page.locator(BUTTON).get_attribute("aria-expanded"), "false")

    def test_event_button_without_javascript(self):
        _, page = self.open_page("/", javascript=False)
        button = page.locator(BUTTON)
        self.assertEqual(button.get_attribute("href"), KRILL)
        self.assertEqual(button.get_attribute("target"), "_blank")
        self.assertEqual(page.locator("iframe").count(), 0)

    def test_open_and_close(self):
        _, page = self.open_page("/")
        button = page.locator(BUTTON)
        self.assertIsNone(button.get_attribute("aria-expanded"))
        button.click()
        self.assertEqual(button.get_attribute("aria-expanded"), "true")
        self.assertEqual(page.locator(FRAME).count(), 1)
        # focus moved into the player
        self.assertTrue(page.evaluate("() => document.activeElement.tagName === 'IFRAME'"))
        button.click()
        self.assertEqual(page.locator(FRAME).count(), 0)
        self.assertEqual(button.get_attribute("aria-expanded"), "false")

    def test_close_button(self):
        _, page = self.open_page("/")
        page.click(BUTTON)
        page.get_by_role("button", name="Close").click()
        self.assertEqual(page.locator(FRAME).count(), 0)
        self.assertEqual(page.locator(BUTTON).get_attribute("aria-expanded"), "false")
        self.assertTrue(page.evaluate("() => document.activeElement.classList.contains('bandcamp-play')"))

    def test_frame_title_and_way_out(self):
        _, page = self.open_page("/")
        page.click(BUTTON)
        self.assertEqual(page.locator(FRAME).get_attribute("title"), "Bandcamp player: Krill")
        more = page.locator(".bandcamp-more")
        self.assertEqual(more.inner_text(), "More by Krill on Bandcamp")
        self.assertEqual(more.get_attribute("href"), KRILL)

    def test_narrow_screen(self):
        context = self.browser.new_context(viewport={"width": 320, "height": 700})
        self.addCleanup(context.close)
        context.route("**/*", self.only_the_test_server)
        _, page = self.open_page("/", context=context)
        page.click(BUTTON)
        frame = page.locator(FRAME)
        frame.scroll_into_view_if_needed()
        box = frame.bounding_box()
        column = page.evaluate("() => document.querySelector('.bandcamp-player').parentElement.getBoundingClientRect().width")
        self.assertLessEqual(box["width"], column + 0.5)
        self.assertLessEqual(box["width"], 320)
        self.assertGreater(box["width"], 200)
        # nothing scrolls sideways
        self.assertTrue(page.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"))

    def test_pressing_play_on_a_band_page(self):
        _, page = self.open_page(self.krill.get_absolute_url())
        self.assertEqual(page.locator("iframe").count(), 0)
        button = page.locator(BUTTON)
        button.click()
        frame = page.locator(FRAME)
        self.assertEqual(frame.count(), 1)
        self.assertTrue(frame.get_attribute("src").startswith("https://bandcamp.com/EmbeddedPlayer/album=111/"))
        self.assertEqual(frame.get_attribute("title"), "Bandcamp player: Krill")
        button.click()
        self.assertEqual(page.locator(FRAME).count(), 0)

    def test_a_band_page_without_javascript_links_to_bandcamp(self):
        _, page = self.open_page(self.krill.get_absolute_url(), javascript=False)
        self.assertEqual(page.locator(BUTTON).get_attribute("href"), KRILL)
        self.assertEqual(page.locator("iframe").count(), 0)
