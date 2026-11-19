"""
the listing's filter and location form, folded into one closed section (index.html). the
section's server markup is checked with the test client, its opening and a filtered submit in
a real browser with and without javascript.
"""

import re

from core.geo_filters import COOKIE_NAME
from core.location import Location, encode
from core.models import CensusPlace, GeoArea
from core.tests.browser import BrowserTestCase
from core.tests.census_fixture import census_places
from core.tests.geo_fixture import load_geo_fixture
from django.test import TestCase


def controls(html):
    match = re.search(r'<div class="listingControls">.*?</div>', html, re.S)
    return match.group(0) if match else None


class ListingControlsTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()
        census_places()

    def html(self, path="/", **cookies):
        for name, value in cookies.items():
            self.client.cookies[name] = value
        return self.client.get(path).content.decode()

    def test_collapsed_by_default(self):
        html = self.html()
        section = controls(html)
        self.assertIn('<details class="controlsFold">', section)
        self.assertNotIn("<details class=\"controlsFold\" open", section)
        self.assertIn('class="geoFilter"', section)
        self.assertIn('class="locationForm"', section)
        self.assertIn("Filters and location", section)
        self.assertNotIn("controlsClear", section)
        self.assertEqual(re.search(r'<details class="calendarSubscribe"[^>]*>', html).group(0), '<details class="calendarSubscribe">')

    def test_the_summary_names_the_state_and_the_location_and_stays_closed(self):
        self.client.cookies["near"] = encode(Location("Somerville, MA", 42.39, -71.1))
        html = self.html("/?state=vermont")
        section = controls(html)
        summary = re.search(r'<span class="controlsSummary">(.*?)</span>', section, re.S).group(1)
        self.assertIn("Vermont", summary)
        self.assertIn("near Somerville, MA", summary)
        self.assertIn('<a class="controlsClear" href="/?clear=1">show all</a>', section)
        self.assertNotIn(" open", re.search(r"<details[^>]*>", section).group(0))
        # opening it shows the values chosen
        self.assertIn('<option value="vermont" selected>Vermont</option>', section)
        self.assertIn("Somerville, MA", section.split("location-current")[1])

    def test_a_filter_and_its_towns_in_the_summary(self):
        summary = re.search(r'<span class="controlsSummary">(.*?)</span>', controls(self.html("/?state=massachusetts")), re.S).group(1)
        self.assertIn("Massachusetts", summary)

    def test_show_all_appears_once(self):
        self.assertEqual(controls(self.html("/?state=vermont")).count("?clear=1"), 1)

    def test_only_the_filter(self):
        CensusPlace.objects.all().delete()
        section = controls(self.html())
        self.assertIn("<summary>Filters", section)
        self.assertNotIn("Filters and location", section)
        self.assertNotIn("locationForm", section)

    def test_only_the_location_form(self):
        GeoArea.objects.all().delete()
        section = controls(self.html())
        self.assertIn("<summary>Location", section)
        self.assertNotIn("geoFilter", section)
        self.assertIn("locationForm", section)

    def test_neither_control_leaves_no_section(self):
        CensusPlace.objects.all().delete()
        GeoArea.objects.all().delete()
        html = self.html()
        self.assertIsNone(controls(html))
        self.assertNotIn("controlsFold", html)

    def test_the_month_archive_has_the_same_section_and_summary(self):
        section = controls(self.html("/2025-02/?state=vermont"))
        self.assertIn("Filters and location", section)
        self.assertIn('<span class="controlsSummary">Vermont</span>', section)
        self.assertIn('<a class="controlsClear" href="/2025-02/?clear=1">show all</a>', section)
        self.assertNotIn(" open", re.search(r"<details[^>]*>", section).group(0))

    def test_discover_and_saved_shows_keep_their_forms_open(self):
        for path in ("/discover", "/saved"):
            html = self.html(path)
            self.assertNotIn("controlsFold", html)
            self.assertNotIn("listingControls", html)
        self.assertIn('class="geoFilter"', self.html("/discover"))
        self.assertIn('class="locationForm"', self.html("/saved"))

    def test_filtering_still_works_and_remembers(self):
        response = self.client.get("/?state=vermont")
        self.assertEqual(response.status_code, 200)
        self.assertIn(COOKIE_NAME, response.cookies)
        self.assertEqual(response.context["geo_filter"].state.slug, "vermont")


class ListingControlsBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        load_geo_fixture()
        census_places()

    def test_opening_and_submitting_the_filter(self):
        _, page = self.open_page("/")
        details = page.locator(".controlsFold")
        self.assertIsNone(details.get_attribute("open"))
        page.click(".controlsFold > summary")
        self.assertIsNotNone(details.get_attribute("open"))
        page.select_option('select[name="state"]', "vermont")
        page.wait_for_url("**/?state=vermont*")
        self.assertIn("Vermont", page.locator(".controlsSummary").inner_text())
        # closed again after the reload, with show all reachable
        self.assertIsNone(page.locator(".controlsFold").get_attribute("open"))
        self.assertTrue(page.locator(".controlsClear").is_visible())

    def test_without_javascript_the_section_opens_and_both_forms_submit(self):
        context, page = self.open_page("/", javascript=False)
        page.click(".controlsFold > summary")
        self.assertTrue(page.locator("form.geoFilter button[type=submit]").is_visible())
        self.assertTrue(page.locator("form.locationForm button[type=submit]").is_visible())
        page.select_option('select[name="state"]', "vermont")
        page.click("form.geoFilter button[type=submit]")
        page.wait_for_url("**/?state=vermont*")
        page.click(".controlsFold > summary")
        page.fill('form.locationForm input[name="q"]', "02144")
        page.click('form.locationForm button[type="submit"]')
        page.wait_for_selector(".controlsSummary")
        self.assertIn("02144", page.locator(".controlsSummary").inner_text())
