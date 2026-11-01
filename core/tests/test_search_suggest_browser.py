"""
the search box's suggestions in a real browser (core/static/core/js/search-suggest.js on
GOV.UK's accessible-autocomplete): kinds tagged and spoken, the keyboard, and the full search
with nothing chosen. nothing outside the test server is fetched (core/tests/browser.py).
"""

from datetime import timedelta

from core.models import Band, Event, Venue
from core.tests.browser import BrowserTestCase
from django.utils import timezone


class SearchSuggestBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        Band.objects.create(name="Belly", city_town="Providence", state="RI")
        paradise = Venue.objects.create(sheet_id="V0001", name="Paradise Rock Club", city_town="Boston", state="MA")
        Event.all_objects.create(title="Paradise birthday", artists="", starttime=timezone.now() + timedelta(days=4), venue=paradise, is_approved=True)

    def search_box(self):
        # any page has the box; /bands has no day map fetching its tiles
        _, page = self.open_page("/bands")
        page.click(".burgerColumn a")
        return page, page.locator(".search input[name=s]")

    def options(self, page):
        page.wait_for_selector(".autocomplete__option")
        return page.locator(".autocomplete__option")

    def test_suggestions_by_kind(self):
        page, box = self.search_box()
        box.press_sequentially("bel")
        options = self.options(page)
        self.assertEqual(options.count(), 1)
        self.assertEqual(options.locator(".suggest-group").inner_text().casefold(), "bands & artists")
        self.assertEqual(options.locator(".suggest-kind").inner_text(), "Band")
        self.assertEqual(options.locator(".suggest-name").inner_text(), "Belly")
        self.assertEqual(page.get_attribute("[role=listbox]", "role"), "listbox")
        self.assertEqual(self.blocked, [])

    def test_each_suggestion_says_what_it_is(self):
        page, box = self.search_box()
        box.press_sequentially("paradise")
        options = self.options(page)
        page.wait_for_function("document.querySelectorAll('.autocomplete__option').length === 2")
        self.assertEqual(options.locator(".suggest-kind").all_inner_texts(), ["Venue", "Show"])
        # what a screen reader hears: the option's accessible name, the visible row being hidden from it
        names = [page.evaluate("el => el.getAttribute('role')", option.element_handle()) for option in options.all()]
        self.assertEqual(names, ["option", "option"])
        self.assertEqual(page.get_by_role("option", name="Paradise Rock Club, venue, Boston, MA").count(), 1)
        self.assertEqual(page.get_by_role("option", name="Paradise birthday, show", exact=False).count(), 1)

    def test_going_straight_to_a_band(self):
        page, box = self.search_box()
        box.press_sequentially("bell")
        self.options(page)
        box.press("ArrowDown")
        with page.expect_navigation():
            page.keyboard.press("Enter")
        self.assertTrue(page.url.endswith("/bands/belly"))

    def test_escape_closes_the_suggestions(self):
        page, box = self.search_box()
        box.press_sequentially("bell")
        self.options(page)
        box.press("Escape")
        page.wait_for_selector(".autocomplete__option", state="hidden")

    def test_running_the_full_search(self):
        page, box = self.search_box()
        box.press_sequentially("belly")
        self.options(page)
        with page.expect_navigation():
            box.press("Enter")
        self.assertTrue(page.url.endswith("/?s=belly"))
        self.assertTrue(page.locator(".search-head").first.text_content().startswith("Bands & artists"))

    def test_too_short(self):
        page, box = self.search_box()
        box.press_sequentially("b")
        page.wait_for_timeout(400)
        self.assertEqual(page.locator(".autocomplete__option").count(), 0)
