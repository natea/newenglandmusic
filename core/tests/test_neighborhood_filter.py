import datetime

from core.models import Event, GeoArea, Venue
from core.tests.browser import BrowserTestCase
from core.tests.geo_fixture import load_geo_fixture
from core.utils_datemath import get_current_new_york_datetime
from django.test import TestCase
from django.utils import timezone


def setup_boston():
    load_geo_fixture()
    soon = get_current_new_york_datetime() + datetime.timedelta(hours=3)
    for title, town, neighborhood in (
        ("west end show", "Boston", "West End"), ("allston show", "Boston", "Allston"),
        ("fenway show", "Boston", "Fenway"), ("cambridge show", "Cambridge", "East Cambridge"),
    ):
        venue = Venue.objects.create(name=f"{title} venue", state="MA", county="Suffolk", city_town=town, neighborhood=neighborhood)
        Event.objects.create(title=title, starttime=soon, venue=venue)
    return GeoArea.objects.get(label__endswith="Boston Metro Region").slug


class NeighborhoodFilterTestCase(TestCase):
    def setUp(self):
        self.metro = setup_boston()

    def titles(self, response):
        return {e.title for day in response.context["grouped_events_as_list"] for e in day["events"]}

    def get(self, towns=(), neighborhoods=()):
        params = [("metro", self.metro)] + [("town", t) for t in towns] + [("neighborhood", n) for n in neighborhoods]
        return self.client.get("/", params)

    def test_two_neighborhoods(self):
        response = self.get(["Boston, MA"], ["West End, Boston, MA", "Allston, Boston, MA"])
        self.assertEqual(self.titles(response), {"west end show", "allston show"})
        html = response.content.decode()
        self.assertIn('<option value="West End, Boston, MA" selected>', html)
        self.assertIn('<option value="Fenway, Boston, MA" >', html)

    def test_no_town_chosen(self):
        response = self.get([], ["West End, Boston, MA"])
        self.assertIn("fenway show", self.titles(response))
        self.assertNotIn('name="neighborhood"', response.content.decode())

    def test_neighborhood_from_another_town(self):
        response = self.get(["Cambridge, MA"], ["West End, Boston, MA"])
        self.assertEqual(self.titles(response), {"cambridge show"})
        self.assertEqual(response.context["geo_filter"].neighborhoods, [])

    def test_remembered_and_in_month_links(self):
        response = self.get(["Boston, MA"], ["West End, Boston, MA"])
        self.assertIn("neighborhood=West+End%2C+Boston%2C+MA", response.context["geo_query"])
        redirect = self.client.get("/")
        self.assertIn("neighborhood=West+End", redirect["Location"])

    def test_calendar_feed(self):
        body = self.client.get(
            "/calendar.ics", [("metro", self.metro), ("town", "Boston, MA"), ("neighborhood", "Allston, Boston, MA")]
        ).content.decode()
        self.assertIn("allston show", body)
        self.assertNotIn("west end show", body)


class NeighborhoodChipsBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        self.metro = setup_boston()

    def test_neighborhood_chips(self):
        _, page = self.open_page(f"/?metro={self.metro}&town=Boston%2C+MA")
        with page.expect_navigation():
            page.select_option("select.neighborhood-add", "West End, Boston, MA")
        self.assertEqual([t.rstrip("×").strip() for t in page.locator(".neighborhood-chip").all_inner_texts()], ["West End, Boston, MA"])
        self.assertEqual(sorted(page.locator("div.event .title-only").all_inner_texts()), ["west end show"])
        with page.expect_navigation():
            page.click(".neighborhood-chip .town-remove")
        self.assertEqual(page.locator(".neighborhood-chip").count(), 0)
        self.assertEqual(len(page.locator("div.event .title-only").all_inner_texts()), 3)
