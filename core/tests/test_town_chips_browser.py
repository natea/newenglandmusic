"""
the town filter's chips in a real browser: picking towns from "add a town" and removing
them with their x, which only javascript does. nothing outside the test server is fetched
(core/tests/browser.py).
"""

import datetime

from core.models import Event, GeoArea, Venue
from core.tests.browser import BrowserTestCase
from core.tests.geo_fixture import load_geo_fixture
from django.utils import timezone


class TownChipsBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        load_geo_fixture()
        soon = timezone.now() + datetime.timedelta(days=1)
        for town in ("Somerville", "Cambridge", "Boston"):
            venue = Venue.objects.create(name=f"{town} venue", state="MA", county="Middlesex", city_town=town)
            Event.objects.create(title=f"{town.lower()} show", starttime=soon, venue=venue)
        self.metro = GeoArea.objects.get(label__endswith="Boston Metro Region").slug

    def titles(self, page):
        return sorted(page.locator("div.event .title-only").all_inner_texts())

    def chips(self, page):
        return [text.rstrip("×").strip() for text in page.locator(".town-chip").all_inner_texts()]

    def test_adding_and_removing_towns(self):
        _, page = self.open_page(f"/?metro={self.metro}")
        self.assertFalse(page.locator('select[name="town"]').is_visible())
        self.assertEqual(self.titles(page), ["boston show", "cambridge show", "somerville show"])

        with page.expect_navigation():
            page.select_option("select.town-add", "Somerville, MA")
        self.assertEqual(self.chips(page), ["Somerville, MA"])
        self.assertEqual(self.titles(page), ["somerville show"])

        with page.expect_navigation():
            page.select_option("select.town-add", "Cambridge, MA")
        self.assertEqual(sorted(self.chips(page)), ["Cambridge, MA", "Somerville, MA"])
        self.assertEqual(self.titles(page), ["cambridge show", "somerville show"])
        # chosen towns aren't offered again
        offered = page.eval_on_selector_all("select.town-add option", "els => els.map(e => e.value)")
        self.assertNotIn("Somerville, MA", offered)

        with page.expect_navigation():
            page.click('.town-chip:has-text("Somerville") .town-remove')
        self.assertEqual(self.chips(page), ["Cambridge, MA"])
        self.assertEqual(self.titles(page), ["cambridge show"])

        with page.expect_navigation():
            page.click(".town-chip .town-remove")
        self.assertEqual(self.chips(page), [])
        self.assertEqual(self.titles(page), ["boston show", "cambridge show", "somerville show"])

    def test_without_javascript_the_plain_multi_select(self):
        _, page = self.open_page(f"/?metro={self.metro}", javascript=False)
        self.assertTrue(page.locator('select[name="town"][multiple]').is_visible())
        self.assertEqual(page.locator(".town-chip").count(), 0)
