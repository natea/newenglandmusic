from datetime import timedelta

from django.test import TestCase

from core.geo_filters import COOKIE_MAX_AGE, COOKIE_NAME
from core.models import Event, GeoArea, Venue
from core.utils_datemath import (
    get_current_new_york_datetime,
    get_previous_current_next_month_start,
)

from .geo_fixture import load_geo_fixture


class GeoFilterPageTestCase(TestCase):
    """the listing pages, filtered by the fixture's regions, states and metros"""

    def setUp(self):
        load_geo_fixture()
        soon = get_current_new_york_datetime() + timedelta(hours=2)
        for title, state, county, city in [
            ("boston show", "MA", "Suffolk", "Boston"),
            ("cape cod show", "MA", "Barnstable", "Hyannis"),
            ("burlington show", "VT", "Chittenden", "Burlington"),
            ("brattleboro show", "VT", "Windham", "Brattleboro"),
            ("providence show", "RI", "Providence", "Providence"),
            ("hartford show", "CT", "Hartford", "Hartford"),
        ]:
            venue = Venue.objects.create(name=f"{city} venue", state=state, county=county, city_town=city)
            Event.objects.create(title=title, starttime=soon, venue=venue)
        Event.objects.create(title="no venue show", starttime=soon, venue_override="somewhere")

    def titles(self, response):
        self.assertEqual(response.status_code, 200)
        return {
            event.title
            for day in response.context["grouped_events_as_list"]
            for event in day["events"]
        }


class FilterListingTestCase(GeoFilterPageTestCase):
    def test_filter_by_state(self):
        response = self.client.get("/?state=vermont")
        self.assertEqual(self.titles(response), {"burlington show", "brattleboro show"})
        self.assertContains(response, '<option value="vermont" selected>Vermont</option>', html=True)

    def test_filter_by_metro_area(self):
        response = self.client.get("/?metro=ma-cape-cod")
        self.assertEqual(self.titles(response), {"cape cod show"})

    def test_filter_by_region(self):
        response = self.client.get("/?region=new-england-south")
        self.assertEqual(
            self.titles(response),
            {"boston show", "cape cod show", "providence show", "hartford show"},
        )

    def test_region_and_state_together(self):
        response = self.client.get("/?region=tri-state&state=vermont")
        self.assertEqual(self.titles(response), set())
        self.assertContains(response, "no events match these filters")
        self.assertContains(response, 'href="/?clear=1"')

    def test_month_archive(self):
        _, _, next_month = get_previous_current_next_month_start(get_current_new_york_datetime())
        venue = Venue.objects.get(name="Burlington venue")
        Event.objects.create(title="next month vt", starttime=next_month + timedelta(days=9, hours=20), venue=venue)
        Event.objects.create(
            title="next month ma",
            starttime=next_month + timedelta(days=9, hours=20),
            venue=Venue.objects.get(name="Boston venue"),
        )
        response = self.client.get(f"/{next_month:%Y-%m}/?state=vermont")
        self.assertEqual(self.titles(response), {"next month vt"})

    def test_no_filter(self):
        response = self.client.get("/")
        self.assertEqual(len(self.titles(response)), 7)
        self.assertNotContains(response, "no events match these filters")

    def test_no_areas_synced_shows_no_form(self):
        GeoArea.objects.all().delete()
        response = self.client.get("/")
        self.assertNotContains(response, 'class="geoFilter"')


class MetroOptionsTestCase(GeoFilterPageTestCase):
    def metro_labels(self, response):
        return [
            (state_label, [metro.short_label for metro in metros])
            for state_label, metros in response.context["metro_groups"]
        ]

    def test_all_metros_grouped_by_state(self):
        response = self.client.get("/")
        self.assertEqual(
            self.metro_labels(response),
            [
                ("Massachusetts", ["Boston", "Boston Metro Region", "Cape Cod", "Central"]),
                ("Vermont", ["North", "South"]),
            ],
        )
        self.assertContains(response, '<optgroup label="Vermont">')

    def test_metros_narrowed_to_the_state(self):
        response = self.client.get("/?state=massachusetts")
        self.assertEqual(
            self.metro_labels(response),
            [("Massachusetts", ["Boston", "Boston Metro Region", "Cape Cod", "Central"])],
        )
        self.assertNotContains(response, "vt-north")

    def test_metro_from_another_state(self):
        response = self.client.get("/?state=massachusetts&metro=vt-north")
        self.assertEqual(self.titles(response), {"boston show", "cape cod show"})
        self.assertIsNone(response.context["geo_filter"].metro)

    def test_state_without_metros(self):
        response = self.client.get("/?state=rhode-island")
        self.assertEqual(self.metro_labels(response), [])
        self.assertNotContains(response, 'name="metro">')


class NavigationAndBadInputTestCase(GeoFilterPageTestCase):
    def test_month_links_keep_the_filter(self):
        _, this_month, next_month = get_previous_current_next_month_start(
            get_current_new_york_datetime()
        )
        response = self.client.get("/?state=vermont")
        self.assertContains(response, f'href="/{next_month:%Y-%m}/?state=vermont"')
        self.assertContains(response, f'href="/{this_month:%Y-%m}/?state=vermont"')
        response = self.client.get(f"/{next_month:%Y-%m}/?state=vermont")
        self.assertEqual(response.context["geo_filter"].state.label, "Vermont")

    def test_unknown_value(self):
        response = self.client.get("/?state=atlantis")
        self.assertEqual(len(self.titles(response)), 7)


class RememberedFilterTestCase(GeoFilterPageTestCase):
    def remember(self, query):
        self.client.cookies[COOKIE_NAME] = query

    def test_filter_is_remembered(self):
        response = self.client.get("/?state=vermont")
        cookie = response.cookies[COOKIE_NAME]
        self.assertEqual(cookie.value, "state=vermont")
        self.assertEqual(cookie["max-age"], COOKIE_MAX_AGE)
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertTrue(cookie["httponly"])
        # the test client keeps the cookie for the next request
        response = self.client.get("/")
        self.assertRedirects(response, "/?state=vermont", fetch_redirect_response=False)

    def test_remembered_filter_with_a_metro(self):
        self.client.get("/?state=massachusetts&metro=ma-cape-cod")
        response = self.client.get("/")
        self.assertRedirects(
            response, "/?state=massachusetts&metro=ma-cape-cod", fetch_redirect_response=False
        )

    def test_remembered_filter_on_a_month_archive(self):
        self.remember("state=vermont")
        response = self.client.get("/2026-11/")
        self.assertRedirects(response, "/2026-11/?state=vermont", fetch_redirect_response=False)

    def test_a_shared_link_wins_over_the_cookie(self):
        self.remember("state=vermont")
        response = self.client.get("/?metro=ma-cape-cod")
        self.assertEqual(self.titles(response), {"cape cod show"})
        self.assertEqual(response.cookies[COOKIE_NAME].value, "metro=ma-cape-cod")

    def test_clearing_by_choosing_all(self):
        self.remember("state=vermont")
        response = self.client.get("/?region=&state=&metro=")
        self.assertEqual(len(self.titles(response)), 7)
        self.assertEqual(response.cookies[COOKIE_NAME].value, "")
        self.assertEqual(response.cookies[COOKIE_NAME]["max-age"], 0)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_clearing_by_the_show_all_link(self):
        self.remember("state=vermont")
        response = self.client.get("/?clear=1")
        self.assertEqual(len(self.titles(response)), 7)
        self.assertEqual(response.cookies[COOKIE_NAME]["max-age"], 0)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_stale_cookie(self):
        self.remember("metro=ma-somewhere-removed")
        response = self.client.get("/")
        self.assertEqual(len(self.titles(response)), 7)
        self.assertEqual(response.cookies[COOKIE_NAME]["max-age"], 0)

    def test_no_filter_chosen(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(COOKIE_NAME, response.cookies)

    def test_unknown_value_leaves_the_cookie_alone(self):
        self.remember("state=vermont")
        response = self.client.get("/?state=atlantis")
        self.assertEqual(len(self.titles(response)), 7)
        self.assertNotIn(COOKIE_NAME, response.cookies)

    def test_search_ignores_the_cookie(self):
        self.remember("state=vermont")
        response = self.client.get("/?s=show")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/search.html")
        self.assertNotIn(COOKIE_NAME, response.cookies)
