"""
the site menu in a real browser, at a wide and a narrow window, with and without javascript.
see core/tests/browser.py.
"""

from core.models import MenuItem
from core.tests.browser import BrowserTestCase

WIDE = {"width": 1280, "height": 800}
NARROW = {"width": 390, "height": 800}


class SiteMenuBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        MenuItem.objects.all().delete()
        for order, (name, url) in enumerate([("Events", "/"), ("Venues", "/venues"), ("Discover bands", "/discover")]):
            MenuItem.objects.create(name=name, url=url, show_in_header=True, order=order)

    def page(self, viewport, javascript=True):
        context = self.browser.new_context(java_script_enabled=javascript, viewport=viewport)
        self.addCleanup(context.close)
        context.route("**/*", self.only_the_test_server)
        return self.open_page("/", context=context)[1]

    def test_links_across_the_top_on_a_wide_screen(self):
        page = self.page(WIDE)
        self.assertTrue(page.locator("#siteMenu a", has_text="Venues").is_visible())
        self.assertTrue(page.locator("#siteMenu a.saved-count").is_visible())
        self.assertFalse(page.locator(".menu-button").is_visible())
        # one row
        tops = {round(box["y"]) for box in (link.bounding_box() for link in page.locator("#siteMenu a").all())}
        self.assertEqual(len(tops), 1)

    def test_the_button_opens_and_closes_the_menu_on_a_phone(self):
        page = self.page(NARROW)
        button = page.locator(".menu-button")
        self.assertTrue(button.is_visible())
        self.assertEqual(button.get_attribute("aria-expanded"), "false")
        self.assertFalse(page.locator("#siteMenu").is_visible())
        button.click()
        self.assertEqual(button.get_attribute("aria-expanded"), "true")
        links = page.locator("#siteMenu a").all()
        self.assertEqual(len(links), 4)
        tops = [link.bounding_box()["y"] for link in links]
        self.assertEqual(tops, sorted(set(tops)))
        button.click()
        self.assertEqual(button.get_attribute("aria-expanded"), "false")
        self.assertFalse(page.locator("#siteMenu").is_visible())

    def test_the_keyboard_opens_and_closes_it(self):
        page = self.page(NARROW)
        page.focus(".menu-button")
        page.keyboard.press("Enter")
        self.assertTrue(page.locator("#siteMenu").is_visible())
        page.keyboard.press("Space")
        self.assertFalse(page.locator("#siteMenu").is_visible())
        page.keyboard.press("Space")
        self.assertEqual(page.get_attribute(".menu-button", "aria-expanded"), "true")

    def test_without_javascript_every_link_shows_and_the_button_does_not(self):
        page = self.page(NARROW, javascript=False)
        self.assertFalse(page.locator(".menu-button").is_visible())
        for name in ("Events", "Venues", "Discover bands", "Saved shows"):
            self.assertTrue(page.locator("#siteMenu a", has_text=name).is_visible(), name)

    def test_the_saved_shows_count_still_updates(self):
        context = self.browser.new_context(viewport=WIDE)
        self.addCleanup(context.close)
        context.route("**/*", self.only_the_test_server)
        context.add_cookies([{"name": "saved_shows", "value": "1,2", "url": self.live_server_url}])
        page = self.open_page("/", context=context)[1]
        self.assertEqual(page.inner_text("a.saved-count"), "Saved shows (2)")
