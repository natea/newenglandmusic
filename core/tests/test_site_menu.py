"""
the one site menu (nav#siteMenu): the same on every page, shown as links on a wide screen
and behind a ☰ button on a narrow one. see core/tests/browser.py for the browser half.
"""

import re

from core.models import Band, MenuItem
from core.tests.browser import BrowserTestCase
from django.test import TestCase

HEADER_ITEMS = [("Events", "/"), ("Venues", "/venues"), ("Artists", "/artists"), ("Discover bands", "/discover"), ("About", "/about")]


def menu_of(html):
    return re.sub(r"\s+", " ", re.search(r"<nav id='siteMenu'.*?</nav>", html, re.S).group(0))


def make_items():
    MenuItem.objects.all().delete()
    for name, url in HEADER_ITEMS:
        MenuItem.objects.create(name=name, url=url, show_in_header=True)
    MenuItem.objects.create(name="Footer only", url="/footer-only", show_in_footer=True)


class SiteMenuTestCase(TestCase):
    def setUp(self):
        make_items()

    def test_the_same_menu_on_every_page(self):
        band = Band.objects.create(name="Belly", city_town="Providence", state="RI")
        paths = ["/", "/2025-02/", "/?s=belly", "/discover", "/bands", f"/bands/{band.slug}", "/saved", "/privacy", "/terms"]
        menus = {path: menu_of(self.client.get(path).content.decode()) for path in paths}
        self.assertEqual(len(set(menus.values())), 1, menus)

    def test_one_list_only(self):
        html = self.client.get("/").content.decode()
        self.assertEqual(html.count("id='siteMenu'"), 1)
        self.assertNotIn("burgerMenuContents", html)
        self.assertNotIn("Footer only</a><br", html)

    def test_header_items_in_order_then_saved_shows_last(self):
        menu = menu_of(self.client.get("/").content.decode())
        links = re.findall(r"<a href=\"([^\"]+)\"", menu)
        self.assertEqual(links, [url for _, url in HEADER_ITEMS] + ["/saved"])
        self.assertIn('class="saved-count">Saved shows</a>', menu)
        self.assertNotIn("/footer-only", menu)
        self.assertNotIn("|", menu)

    def test_edits_in_the_admin_show_everywhere(self):
        item = MenuItem.objects.get(url="/venues")
        item.name = "Rooms"
        item.save()
        MenuItem.objects.filter(url="/about").update(show_in_header=False)
        for path in ("/", "/discover", "/saved"):
            menu = menu_of(self.client.get(path).content.decode())
            self.assertIn(">Rooms</a>", menu)
            self.assertNotIn(">About</a>", menu)

    def test_a_real_button_and_a_head_snippet_for_the_js_class(self):
        html = self.client.get("/").content.decode()
        self.assertIn("<button type='button' class='menu-toggle' aria-expanded='false' aria-controls='siteMenu' aria-label='Menu'>", html)
        self.assertLess(html.index("classList.add('js')"), html.index("<link href"))
        self.assertIn("core/js/site_menu.js", html)


class SiteMenuBrowserTestCase(BrowserTestCase):
    WIDE = {"width": 1200, "height": 800}
    NARROW = {"width": 400, "height": 800}

    def setUp(self):
        super().setUp()
        make_items()

    def page(self, size, javascript=True):
        context, page = self.open_page(javascript=javascript)
        page.set_viewport_size(size)
        return page

    def test_links_across_the_top_on_a_wide_screen(self):
        page = self.page(self.WIDE)
        self.assertFalse(page.locator(".menu-toggle").is_visible())
        links = page.locator("#siteMenu a")
        self.assertEqual(links.count(), len(HEADER_ITEMS) + 1)
        for i in range(links.count()):
            self.assertTrue(links.nth(i).is_visible())

    def test_the_button_opens_and_closes_the_stacked_list_on_a_narrow_screen(self):
        page = self.page(self.NARROW)
        button = page.locator(".menu-toggle")
        self.assertTrue(button.is_visible())
        self.assertEqual(button.get_attribute("aria-expanded"), "false")
        self.assertFalse(page.locator("#siteMenu").is_visible())
        button.click()
        self.assertEqual(button.get_attribute("aria-expanded"), "true")
        links = page.locator("#siteMenu a")
        tops = [links.nth(i).bounding_box()["y"] for i in range(links.count())]
        self.assertEqual(tops, sorted(set(tops)))
        button.click()
        self.assertEqual(button.get_attribute("aria-expanded"), "false")
        self.assertFalse(page.locator("#siteMenu").is_visible())

    def test_the_keyboard_opens_and_closes_it(self):
        page = self.page(self.NARROW)
        button = page.locator(".menu-toggle")
        button.focus()
        page.keyboard.press("Enter")
        self.assertEqual(button.get_attribute("aria-expanded"), "true")
        page.keyboard.press("Space")
        self.assertEqual(button.get_attribute("aria-expanded"), "false")
        page.keyboard.press("Space")
        self.assertTrue(page.locator("#siteMenu").is_visible())

    def test_without_javascript_every_link_shows_and_the_button_does_not(self):
        page = self.page(self.NARROW, javascript=False)
        self.assertFalse(page.locator(".menu-toggle").is_visible())
        links = page.locator("#siteMenu a")
        for i in range(links.count()):
            self.assertTrue(links.nth(i).is_visible())
