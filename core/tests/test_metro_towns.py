from datetime import timedelta

from core.geo_filters import COOKIE_NAME
from core.models import Event, GeoArea, Venue
from core.utils_datemath import get_current_new_york_datetime

from .test_index_geo_filter import GeoFilterPageTestCase


class MetroTownsTestCase(GeoFilterPageTestCase):
    def setUp(self):
        super().setUp()
        soon = get_current_new_york_datetime() + timedelta(hours=3)
        for title, city in (("somerville show", "Somerville"), ("cambridge show", "Cambridge"), ("cambridge late show", "cambridge")):
            venue = Venue.objects.create(name=f"{title} venue", state="MA", county="Middlesex", city_town=city)
            Event.objects.create(title=title, starttime=soon, venue=venue)
        self.metro = GeoArea.objects.get(label__endswith="Boston Metro Region").slug

    def get(self, *towns, metro=True, **extra):
        params = [("metro", self.metro)] if metro else []
        return self.client.get("/", params + [("town", town) for town in towns], **extra)

    def test_two_towns_in_a_metro(self):
        response = self.get("Somerville, MA", "Cambridge, MA")
        self.assertEqual(self.titles(response), {"somerville show", "cambridge show", "cambridge late show"})
        html = response.content.decode()
        self.assertIn('<option value="Somerville, MA" selected>', html)
        self.assertIn('<option value="Cambridge, MA" selected>', html)

    def test_towns_offered(self):
        response = self.get()
        self.assertEqual(response.context["metro_towns"], ["Boston, MA", "Cambridge, MA", "Somerville, MA"])
        self.assertIn('name="town" multiple', response.content.decode())

    def test_no_towns_without_a_metro(self):
        self.assertNotIn('name="town"', self.client.get("/?state=massachusetts").content.decode())

    def test_town_outside_the_metro(self):
        response = self.get("Burlington, VT")
        self.assertEqual(self.titles(response), {"boston show", "somerville show", "cambridge show", "cambridge late show"})
        self.assertNotIn(" selected>Burlington", response.content.decode())

    def test_town_without_a_metro(self):
        response = self.get("Somerville, MA", metro=False)
        self.assertIn("burlington show", self.titles(response))

    def test_remembered(self):
        self.get("Somerville, MA")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("town=Somerville%2C+MA", response["Location"])
        self.assertIn("town=Somerville", self.client.cookies[COOKIE_NAME].value)

    def test_month_links_keep_towns(self):
        self.assertIn("town=Somerville%2C+MA", self.get("Somerville, MA").context["geo_query"])

    def test_calendar_feed(self):
        response = self.client.get("/calendar.ics", [("metro", self.metro), ("town", "Somerville, MA")])
        body = response.content.decode()
        self.assertIn("somerville show", body)
        self.assertNotIn("cambridge show", body)
        self.assertNotIn("boston show", body)

    def test_changing_the_metro_drops_other_towns(self):
        cape = GeoArea.objects.get(label__endswith="Cape Cod").slug
        response = self.client.get("/", [("metro", cape), ("town", "Somerville, MA")])
        self.assertEqual(response.context["geo_filter"].towns, [])
        self.assertEqual(self.titles(response), {"cape cod show"})

    def test_works_without_javascript(self):
        # a plain multi-select in a GET form with a submit button
        html = self.get().content.decode()
        form = html[html.index('<form class="geoFilter"'):html.index("</form>", html.index('<form class="geoFilter"'))]
        self.assertIn('method="get"', form)
        self.assertIn('<select name="town" multiple', form)
        self.assertIn('<button type="submit">filter</button>', form)
