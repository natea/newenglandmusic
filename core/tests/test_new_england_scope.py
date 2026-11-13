"""
the public site lists only events at New England venues (core/geo_filters.py NEW_ENGLAND_STATES),
while the admin, the pipeline and direct event links still see every event
"""

import datetime
from io import StringIO
from unittest import mock

from core.geo_filters import NEW_ENGLAND_STATES
from core.models import Artist, Band, Event, EventPerformer, SpotifyArtistLink, Venue
from core.sitemap import SiteSitemap
from core.tests.spotify_fixture import CREDENTIALS, FakeSpotify, fixture
from core.views.act_index import live_acts
from core.utils_datemath import get_current_new_york_datetime
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from icalendar import Calendar


class ScopeTestCase(TestCase):
    def setUp(self):
        self.vermont = Venue.objects.create(sheet_id="V1", name="Higher Ground", city_town="Burlington", state="VT")
        self.new_york = Venue.objects.create(sheet_id="V2", name="Brooklyn Bowl", city_town="Brooklyn", state="NY")
        self.jersey = Venue.objects.create(sheet_id="V3", name="Stone Pony", city_town="Asbury Park", state="NJ")
        self.pennsylvania = Venue.objects.create(sheet_id="V4", name="World Cafe Live", city_town="Philadelphia", state="PA")
        self.soon = timezone.now() + datetime.timedelta(hours=3)

    def show(self, title, venue, when=None, **fields):
        return Event.objects.create(title=title, starttime=when or self.soon, venue=venue, **fields)

    def act_show(self, act, venue, days=3):
        event = self.show("show", venue, timezone.now() + datetime.timedelta(days=days))
        EventPerformer.objects.create(event=event, **({"band": act} if isinstance(act, Band) else {"artist": act}))
        return event


class ListingTestCase(ScopeTestCase):
    def test_listing_hides_a_new_york_show(self):
        self.show("vermont show", self.vermont)
        self.show("new york show", self.new_york)
        response = self.client.get("/")
        self.assertContains(response, "vermont show")
        self.assertNotContains(response, "new york show")

    def test_an_event_without_a_linked_venue(self):
        Event.objects.create(title="floating show", starttime=self.soon, venue_override="a field")
        self.assertNotContains(self.client.get("/"), "floating show")
        self.assertNotContains(self.client.get("/", {"s": "floating"}), "floating show")

    def test_a_lowercase_venue_state_is_out(self):
        # the sheet sync writes states uppercase, so a lowercase one isn't a New England venue
        lower = Venue.objects.create(sheet_id="V5", name="Lower Hall", state="ma")
        self.show("lowercase show", lower)
        self.assertNotContains(self.client.get("/"), "lowercase show")

    def test_widening_the_list(self):
        self.show("new york show", self.new_york)
        self.assertNotContains(self.client.get("/"), "new york show")
        with mock.patch("core.geo_filters.NEW_ENGLAND_STATES", [*NEW_ENGLAND_STATES, "NY"]):
            self.assertContains(self.client.get("/"), "new york show")

    def test_month_archive(self):
        month = get_current_new_york_datetime().strftime("%Y-%m")
        self.show("new york show", self.new_york)
        self.show("vermont show", self.vermont)
        response = self.client.get(f"/{month}/")
        self.assertContains(response, "vermont show")
        self.assertNotContains(response, "new york show")

    def test_a_direct_link_still_opens(self):
        event = self.show("new york show", self.new_york)
        self.assertContains(self.client.get(f"/event/{event.pk}"), "new york show")


class SearchTestCase(ScopeTestCase):
    def test_search_hides_a_new_jersey_show(self):
        self.show("pony show", self.jersey)
        self.show("pony party", self.vermont)
        response = self.client.get("/", {"s": "pony"})
        self.assertEqual([e.title for e in response.context["upcoming_shows"]], ["pony party"])
        self.assertNotContains(response, "pony show")

    def test_search_suggestions(self):
        self.show("pony show", self.jersey)
        self.show("pony party", self.vermont)
        items = self.client.get("/search/suggest", {"q": "pony"}).json()["items"]
        self.assertEqual([item["name"] for item in items if item["kind"] == "show"], ["pony party"])


class FeedTestCase(ScopeTestCase):
    def summaries(self, url):
        entries = Calendar.from_ical(self.client.get(url).content).walk("VEVENT")
        return {str(entry["SUMMARY"]).split(" [")[0] for entry in entries}

    def test_calendar_feed_outside_new_england(self):
        self.show("vermont show", self.vermont)
        self.show("new york show", self.new_york)
        self.assertEqual(self.summaries("/calendar.ics"), {"vermont show"})

    def test_a_feed_for_a_state_in_new_england(self):
        self.show("vermont show", self.vermont)
        self.assertEqual(self.summaries("/calendar.ics?state=vermont"), {"vermont show"})


class ActsTestCase(ScopeTestCase):
    def test_act_page(self):
        band = Band.objects.create(name="Belly")
        self.act_show(band, self.vermont)
        pennsylvania = self.act_show(band, self.pennsylvania, days=4)
        response = self.client.get(band.get_absolute_url())
        self.assertEqual([event.venue.state for event in response.context["shows"]], ["VT"])
        self.assertContains(response, "Higher Ground")
        self.assertNotContains(response, "World Cafe Live")
        self.assertNotContains(response, f"/event/{pennsylvania.pk}")

    def test_next_show_dates(self):
        near = Band.objects.create(name="Belly")
        far = Artist.objects.create(name="Bellwether")
        self.act_show(near, self.new_york, days=2)
        self.act_show(far, self.vermont, days=5)
        self.act_show(far, self.new_york, days=1)
        entries = {act.name: act.next_show for act in live_acts()}
        self.assertIsNone(entries["Belly"])
        self.assertEqual(entries["Bellwether"].date(), (timezone.now() + datetime.timedelta(days=5)).date())

    def test_next_show_in_the_search_results(self):
        band = Band.objects.create(name="Belly")
        self.act_show(band, self.new_york, days=2)
        self.assertNotContains(self.client.get("/", {"s": "belly"}), 'class="index-next"')
        self.act_show(band, self.vermont, days=5)
        self.assertContains(self.client.get("/", {"s": "belly"}), 'class="index-next"')

    def test_discover(self):
        band = Band.objects.create(name="Outsiders")
        self.act_show(band, self.new_york)
        self.assertNotContains(self.client.get("/discover"), "Outsiders")
        home = Band.objects.create(name="Locals")
        self.act_show(home, self.vermont)
        self.assertContains(self.client.get("/discover"), "Locals")


class SavedShowsTestCase(ScopeTestCase):
    def test_saved_shows(self):
        pennsylvania = self.show("philly show", self.pennsylvania)
        vermont = self.show("vermont show", self.vermont)
        self.client.cookies["saved_shows"] = f"{pennsylvania.pk}%2C{vermont.pk}"
        response = self.client.get("/saved")
        self.assertContains(response, "vermont show")
        self.assertNotContains(response, "philly show")


class SitemapTestCase(ScopeTestCase):
    def test_sitemap_months(self):
        soon = timezone.now() + datetime.timedelta(days=400)
        self.show("far show", self.new_york, soon)
        month = f"/{get_current_new_york_datetime().year + 1}-"
        self.assertFalse([url for url in SiteSitemap().items() if url.startswith(month)])
        self.show("local far show", self.vermont, soon)
        self.assertTrue([url for url in SiteSitemap().items() if url.startswith(month)])


class UntouchedTestCase(ScopeTestCase):
    def test_admin_and_data_untouched(self):
        self.show("new york show", self.new_york, is_approved=True)
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.assertContains(self.client.get("/admin/core/alleventproxy/"), "new york show")
        self.assertTrue(Event.objects.filter(title="new york show").exists())
        self.assertTrue(Venue.objects.filter(state="NY").exists())

    @mock.patch.dict("os.environ", CREDENTIALS)
    def test_artist_matching_unchanged(self):
        self.show("new york show", self.new_york, artists="The Ballroom Thieves")
        spotify = FakeSpotify({"The Ballroom Thieves": fixture("search_unique.json")})
        with spotify.patch():
            call_command("match_spotify_artists", stdout=StringIO())
        found = SpotifyArtistLink.objects.get(name_key="ballroom thieves")
        self.assertEqual(found.status, SpotifyArtistLink.Status.MATCHED)
