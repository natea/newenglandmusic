"""
the one site menu (nav#siteMenu): the same on every page, a single list, and the menu items
the admin marks for the header. the narrow and wide layouts are in test_site_menu_browser.py.
"""

import datetime
import re

from core.models import Band, Event, MenuItem, Venue
from django.test import TestCase
from django.utils import timezone


def menu(html):
    found = re.findall(r"<nav id='siteMenu'.*?</nav>", html, re.S)
    assert len(found) == 1, f"{len(found)} menus"
    return re.sub(r"\s+", " ", found[0])


class SiteMenuTestCase(TestCase):
    def setUp(self):
        MenuItem.objects.all().delete()
        for order, (name, url) in enumerate(
            [("Events", "/"), ("Venues", "/venues"), ("Artists", "/artists"), ("About", "/about"), ("Discover bands", "/discover")]
        ):
            MenuItem.objects.create(name=name, url=url, show_in_header=True, order=order)
        MenuItem.objects.create(name="Contact", url="/contact", show_in_footer=True)
        self.venue = Venue.objects.create(sheet_id="V1", name="Paradise Rock Club", city_town="Boston", state="MA")
        self.band = Band.objects.create(name="Belly")

    def paths(self):
        now = timezone.now()
        return [
            "/", f"/{now:%Y-%m}/", "/?s=belly", "/discover", "/bands", "/saved", "/privacy",
            self.band.get_absolute_url(),
        ]

    def test_the_same_menu_on_every_page(self):
        menus = {path: menu(self.client.get(path).content.decode()) for path in self.paths()}
        self.assertEqual(len(set(menus.values())), 1, menus)

    def test_one_list_only(self):
        html = self.client.get("/").content.decode()
        self.assertEqual(html.count("id='siteMenu'"), 1)
        self.assertNotIn("burgerMenuContents", html)
        # the footer-only item isn't in the header
        self.assertNotIn("Contact", menu(html))

    def test_the_header_items_in_order_then_saved_shows(self):
        links = re.findall(r"<a href=\"([^\"]*)\"[^>]*>([^<]*)</a>", menu(self.client.get("/").content.decode()))
        self.assertEqual(
            links,
            [("/", "Events"), ("/venues", "Venues"), ("/artists", "Artists"), ("/about", "About"),
             ("/discover", "Discover bands"), ("/saved", "Saved shows")],
        )

    def test_edits_in_the_admin_show_everywhere(self):
        MenuItem.objects.filter(url="/about").update(name="Who we are")
        MenuItem.objects.filter(url="/venues").update(show_in_header=False)
        for path in self.paths():
            html = menu(self.client.get(path).content.decode())
            self.assertIn("Who we are", html, path)
            self.assertNotIn(">Venues<", html, path)

    def test_the_button_is_a_real_closed_button(self):
        html = self.client.get("/").content.decode()
        self.assertIn(
            '<button type="button" class="menu-button" aria-expanded="false" aria-controls="siteMenu" aria-label="Menu">', html
        )

    def test_the_saved_shows_link_keeps_its_count_element(self):
        self.assertIn('<a href="/saved" class="saved-count">Saved shows</a>', menu(self.client.get("/").content.decode()))
