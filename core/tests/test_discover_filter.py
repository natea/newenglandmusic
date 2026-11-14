"""the discovery deck's region, state and metro filter and its remembered filter, as the listing's"""

import os
from unittest import mock

from core.geo_filters import COOKIE_NAME
from core.models import Artist, Band
from core.saved_shows import COOKIE_NAME as SAVED_COOKIE
from core.tests.discover_fixture import days, show, venue
from core.tests.geo_fixture import load_geo_fixture
from core.tests.spotify_fixture import CREDENTIALS as SPOTIFY_ON
from django.test import TestCase


class DeckFilterBase(TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict(os.environ, SPOTIFY_ON))
        load_geo_fixture()
        self.providence = venue("Lupo's", "Providence", "RI", "V1")
        self.burlington = venue("Nectar's", "Burlington", "VT", "V2")
        self.boston = venue("Paradise", "Boston", "MA", "V3")
        self.somerville = venue("Once", "Somerville", "MA", "V4")
        self.belly = Band.objects.create(name="Belly", city_town="Providence", state="RI")
        self.anjimile = Artist.objects.create(name="Anjimile", city_town="Boston", state="MA")

    def get(self, query=""):
        response = self.client.get(f"/discover{query}")
        self.assertEqual(response.status_code, 200)
        return response

    def names(self, response):
        return [card.act.name for card in response.context["cards"]]

    def shows_of(self, response, name):
        card = next(card for card in response.context["cards"] if card.act.name == name)
        return [event.venue.name for event in card.shows]


class DeckFilterTestCase(DeckFilterBase):
    def test_no_filter_belly_with_only_a_rhode_island_show_is_in_the_deck(self):
        show(self.belly, days(3), self.providence)
        self.assertEqual(self.names(self.get()), ["Belly"])

    def test_filter_by_state(self):
        show(self.belly, days(3), self.burlington)
        show(self.anjimile, days(2), self.providence)
        response = self.get("?state=vermont")
        self.assertEqual(self.names(response), ["Belly"])
        self.assertContains(response, '<option value="vermont" selected>Vermont</option>', html=True)

    def test_a_card_and_its_picker_list_only_the_areas_shows(self):
        show(self.belly, days(5), self.providence)
        show(self.belly, days(3), self.burlington)
        response = self.get("?state=vermont")
        self.assertEqual(self.shows_of(response, "Belly"), ["Nectar's"])
        html = response.content.decode()
        self.assertIn("Nectar&#x27;s", html)
        self.assertNotIn("Lupo&#x27;s", html)
        # unfiltered, the same card lists both, soonest first
        self.assertEqual(self.shows_of(self.get("?clear=1"), "Belly"), ["Nectar's", "Lupo's"])

    def test_an_act_with_no_show_in_the_area_is_left_out(self):
        show(self.anjimile, days(3), self.providence)
        self.assertEqual(self.names(self.get("?state=vermont")), [])

    def test_a_show_with_no_venue_matches_no_filter(self):
        show(self.belly, days(3), venue=None)
        self.assertEqual(self.names(self.get("?state=massachusetts")), [])
        # and isn't in the deck at all: the site lists only new england's shows (new-england-scope)
        self.assertEqual(self.names(self.get("?clear=1")), [])

    def test_filter_by_region(self):
        show(self.belly, days(3), self.providence)
        show(self.anjimile, days(2), self.burlington)
        self.assertEqual(self.names(self.get("?region=new-england-south")), ["Belly"])

    def test_filter_by_metro_and_by_a_town_in_it(self):
        show(self.belly, days(3), self.providence)
        show(self.anjimile, days(2), self.boston)
        show(Band.objects.create(name="Frankie Cosmos"), days(4), self.somerville)
        self.assertEqual(self.names(self.get("?metro=ma-boston-metro-region")), ["Anjimile", "Frankie Cosmos"])
        response = self.get("?metro=ma-boston-metro-region&town=Somerville, MA")
        self.assertEqual(self.names(response), ["Frankie Cosmos"])

    def test_region_and_state_together(self):
        show(self.belly, days(3), self.burlington)
        self.assertEqual(self.names(self.get("?region=new-england-south&state=vermont")), [])
        # a region outside new england isn't offered, so it's ignored like any unknown value
        self.assertEqual(self.names(self.get("?region=tri-state&state=vermont")), ["Belly"])

    def test_an_unknown_value_gives_the_unfiltered_deck(self):
        show(self.belly, days(3), self.providence)
        self.assertEqual(self.names(self.get("?state=atlantis")), ["Belly"])

    def test_metro_options_follow_the_state(self):
        response = self.get("?state=massachusetts")
        groups = [(label, [m.short_label for m in metros]) for label, metros in response.context["metro_groups"]]
        self.assertEqual([label for label, _ in groups], ["Massachusetts"])

    def test_order_follows_the_filter(self):
        show(self.belly, days(1), self.providence)
        show(self.belly, days(150), self.burlington)
        show(self.anjimile, days(30), self.burlington)
        self.assertEqual(self.names(self.get("?clear=1")), ["Belly", "Anjimile"])
        self.assertEqual(self.names(self.get("?state=vermont")), ["Anjimile", "Belly"])


class DeckFormTestCase(DeckFilterBase):
    def test_the_form_has_the_options_and_selected_values(self):
        show(self.belly, days(3), self.burlington)
        response = self.get("?state=vermont")
        self.assertEqual(response.context["geo_filter"].state.slug, "vermont")
        self.assertTrue(response.context["region_options"])
        self.assertContains(response, '<form class="geoFilter" method="get" action="/discover">')
        self.assertContains(response, 'name="region"')
        self.assertContains(response, 'name="metro"')

    def test_nothing_matches_the_filters(self):
        show(self.belly, days(3), self.providence)
        response = self.get("?state=vermont")
        self.assertContains(response, "No bands match these filters")
        self.assertContains(response, 'href="/discover?clear=1"')

    def test_an_empty_deck_without_a_filter_has_the_plain_message(self):
        response = self.get()
        self.assertContains(response, "There are no bands to discover yet")
        self.assertNotContains(response, "match these filters")


class DeckRememberedFilterTestCase(DeckFilterBase):
    def test_a_filter_set_on_the_deck_redirects_the_listing(self):
        self.get("?state=vermont")
        self.assertRedirects(self.client.get("/"), "/?state=vermont", fetch_redirect_response=False)

    def test_a_cookie_redirects_a_bare_deck(self):
        self.client.cookies[COOKIE_NAME] = "state=vermont"
        self.assertRedirects(self.client.get("/discover"), "/discover?state=vermont", fetch_redirect_response=False)

    def test_the_menus_bare_link_and_trailing_slash(self):
        self.client.cookies[COOKIE_NAME] = "state=vermont"
        response = self.client.get("/discover/")
        self.assertRedirects(response, "/discover", status_code=301, fetch_redirect_response=False)
        response = self.client.get("/discover")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/discover?state=vermont")
        self.assertIn("no-store", response["Cache-Control"])

    def test_clearing(self):
        self.client.cookies[COOKIE_NAME] = "state=vermont"
        response = self.get("?clear=1")
        self.assertEqual(response.cookies[COOKIE_NAME]["max-age"], 0)

    def test_a_stale_cookie_is_deleted_without_a_redirect(self):
        show(self.belly, days(3), self.providence)
        self.client.cookies[COOKIE_NAME] = "metro=ma-somewhere-removed"
        response = self.get()
        self.assertEqual(self.names(response), ["Belly"])
        self.assertEqual(response.cookies[COOKIE_NAME]["max-age"], 0)

    def test_the_url_wins_over_the_cookie(self):
        show(self.belly, days(3), self.providence)
        show(self.anjimile, days(3), self.burlington)
        self.client.cookies[COOKIE_NAME] = "state=rhode-island"
        response = self.get("?state=vermont")
        self.assertEqual(self.names(response), ["Anjimile"])
        self.assertEqual(response.cookies[COOKIE_NAME].value, "state=vermont")

    def test_the_bookmark_returns_to_the_filtered_url(self):
        event = show(self.belly, days(3), self.burlington)
        html = self.get("?state=vermont").content.decode()
        self.assertIn(f'name="next" value="/discover?state=vermont#bands-belly-event-{event.pk}"', html)
        response = self.client.post(
            f"/saved/toggle/{event.pk}", {"next": f"/discover?state=vermont#bands-belly-event-{event.pk}"}
        )
        self.assertRedirects(
            response, f"/discover?state=vermont#bands-belly-event-{event.pk}", fetch_redirect_response=False
        )
        self.assertIn(SAVED_COOKIE, response.cookies)
