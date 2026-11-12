import os
from unittest import mock

from core.artist_previews import act_previews
from core.models import Artist, Band
from core.tests.apple_music_fixture import SWITCHED_ON as APPLE_ON
from core.tests.discover_fixture import apple, days, show, spotify, venue, youtube
from core.tests.spotify_fixture import CREDENTIALS as SPOTIFY_ON
from core.tests.youtube_fixture import SWITCHED_ON as YOUTUBE_ON
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext


class DiscoverTestCase(TestCase):
    def setUp(self):
        self.lupo = venue()
        self.belly = Band.objects.create(name="Belly", city_town="Providence", state="RI")
        self.anjimile = Artist.objects.create(name="Anjimile", city_town="Boston", state="MA")

    def page(self):
        response = self.client.get("/discover")
        self.assertEqual(response.status_code, 200)
        return response

    def names(self, response):
        return sorted(card.act.name for card in response.context["cards"])


class DeckTestCase(DiscoverTestCase):
    def test_an_act_with_an_upcoming_show(self):
        show(self.belly, days(7), self.lupo)
        self.assertEqual(self.names(self.page()), ["Belly"])

    def test_acts_left_out(self):
        show(self.anjimile, days(-3), self.lupo)
        held = Band.objects.create(name="3 1/2 Girls", needs_review=True)
        show(held, days(5), self.lupo)
        self.assertEqual(self.names(self.page()), [])

    def test_an_unapproved_upcoming_show_does_not_count(self):
        show(self.belly, days(5), self.lupo, approved=False)
        self.assertEqual(self.names(self.page()), [])

    def test_cancelled_shows(self):
        live = show(self.belly, days(9), self.lupo)
        show(self.belly, days(5), self.lupo, cancelled=True)
        show(self.anjimile, days(6), self.lupo, cancelled=True)
        response = self.page()
        self.assertEqual(self.names(response), ["Belly"])
        self.assertEqual([event.pk for event in response.context["cards"][0].shows], [live.pk])

    def test_one_card_for_several_shows(self):
        events = [show(self.belly, days(n), self.lupo) for n in (20, 7, 13)]
        cards = self.page().context["cards"]
        self.assertEqual(len(cards), 1)
        # soonest first
        self.assertEqual([event.pk for event in cards[0].shows], [events[1].pk, events[2].pk, events[0].pk])

    def test_a_show_from_earlier_today_counts(self):
        # the band page's bound is the start of today, so the deck agrees
        from core.utils_datemath import beginning_of_day, get_current_new_york_datetime

        show(self.belly, beginning_of_day(get_current_new_york_datetime()), self.lupo)
        self.assertEqual(self.names(self.page()), ["Belly"])

    def test_the_empty_page(self):
        response = self.page()
        self.assertContains(response, "There are no bands to discover yet")
        self.assertContains(response, '<a href="/">listings</a>', html=False)

    def test_the_area_filter_is_ignored_and_kept(self):
        show(self.belly, days(3), self.lupo)
        self.client.cookies["geo_filter"] = "vt"
        self.client.get("/discover")
        self.assertEqual(self.names(self.page()), ["Belly"])
        self.assertEqual(self.client.cookies["geo_filter"].value, "vt")

    def test_a_random_order_each_visit_which_tests_can_fix(self):
        for n, act in enumerate((self.belly, self.anjimile)):
            show(act, days(n + 1), self.lupo)
        with mock.patch("core.views.discover.random.shuffle", lambda cards: cards.sort(key=lambda c: c.act.name)):
            self.assertEqual([c.act.name for c in self.page().context["cards"]], ["Anjimile", "Belly"])
        with mock.patch("core.views.discover.random.shuffle", lambda cards: cards.sort(key=lambda c: c.act.name, reverse=True)):
            self.assertEqual([c.act.name for c in self.page().context["cards"]], ["Belly", "Anjimile"])

    def test_not_cached(self):
        cache_control = self.page()["Cache-Control"]
        self.assertIn("no-store", cache_control)
        self.assertIn("private", cache_control)

    def test_a_trailing_slash_is_dropped(self):
        response = self.client.get("/discover/")
        self.assertRedirects(response, "/discover", status_code=301, fetch_redirect_response=False)

    def test_the_queries_do_not_grow_with_the_acts(self):
        def add_acts(numbers):
            for n in numbers:
                show(Band.objects.create(name=f"Act {n}"), days(n + 1), venue(f"Venue {n}", sheet_id=f"X{n}"))
                spotify(f"act {n}", f"id{n}")
                apple(f"act {n}")
                youtube(f"act {n}")

        env = mock.patch.dict(os.environ, {**SPOTIFY_ON, **APPLE_ON, **YOUTUBE_ON})
        env.start()
        self.addCleanup(env.stop)
        add_acts(range(2))
        with CaptureQueriesContext(connection) as queries:
            self.page()
        add_acts(range(2, 12))
        with self.assertNumQueries(len(queries)):
            self.page()


class ActPreviewsTestCase(DiscoverTestCase):
    def previews(self, name="Belly"):
        return act_previews([name]).get("belly" if name == "Belly" else name.lower())

    def test_nothing_matched(self):
        with mock.patch.dict(os.environ, {**SPOTIFY_ON, **APPLE_ON, **YOUTUBE_ON}):
            self.assertIsNone(self.previews())

    def test_apple_music_only(self):
        apple("belly")
        with mock.patch.dict(os.environ, APPLE_ON):
            preview = self.previews()
        self.assertEqual(preview["apple"], {"artist": "100", "song": "200", "album": "300"})
        self.assertIsNone(preview["youtube"])
        self.assertIsNone(preview["spotify"])

    def test_youtube_only(self):
        youtube("belly")
        with mock.patch.dict(os.environ, YOUTUBE_ON):
            preview = self.previews()
        self.assertEqual(preview["youtube"], {"video": "vid123", "channel": "UCchannel"})
        self.assertIsNone(preview["apple"])

    def test_all_three(self):
        youtube("belly")
        apple("belly")
        spotify("belly")
        with mock.patch.dict(os.environ, {**SPOTIFY_ON, **APPLE_ON, **YOUTUBE_ON}):
            preview = self.previews()
        self.assertTrue(preview["youtube"] and preview["apple"] and preview["spotify"] == "sp123")

    def test_an_apple_match_without_a_top_song_has_no_apple_button(self):
        apple("belly", song_id="")
        spotify("belly")
        with mock.patch.dict(os.environ, {**SPOTIFY_ON, **APPLE_ON}):
            preview = self.previews()
        self.assertIsNone(preview["apple"])
        self.assertEqual(preview["spotify"], "sp123")

    def test_an_apple_match_without_a_top_song_alone_has_nothing(self):
        apple("belly", album_id="")
        with mock.patch.dict(os.environ, APPLE_ON):
            self.assertIsNone(self.previews())

    def test_switches_off_and_credentials_missing(self):
        youtube("belly")
        apple("belly")
        spotify("belly")
        with mock.patch.dict(os.environ, {}, clear=False):
            for key in (*SPOTIFY_ON, *APPLE_ON, *YOUTUBE_ON):
                os.environ.pop(key, None)
            self.assertIsNone(self.previews())

    def test_only_the_acts_own_name_matches(self):
        spotify("belly")
        apple("belly")
        youtube("belly")
        with mock.patch.dict(os.environ, {**SPOTIFY_ON, **APPLE_ON, **YOUTUBE_ON}):
            # a duo's parts and an occasion's first words are not the act's name
            self.assertEqual(act_previews(["Belly & Anjimile", "Belly Fall 2026 Tour"]), {})

    def test_the_page_has_the_order_youtube_apple_spotify_with_icons(self):
        show(self.belly, days(3), self.lupo)
        youtube("belly")
        apple("belly")
        spotify("belly")
        with mock.patch.dict(os.environ, {**SPOTIFY_ON, **APPLE_ON, **YOUTUBE_ON}):
            html = self.page().content.decode()
        positions = [html.index(f'class="{name}-play"') for name in ("youtube", "apple", "spotify")]
        self.assertEqual(positions, sorted(positions))
        for icon in ("icon-youtube", "icon-apple-music", "icon-spotify"):
            self.assertIn(f'href="#{icon}"', html)
            self.assertIn(f'id="{icon}"', html)


class CardTestCase(DiscoverTestCase):
    def test_card_contents(self):
        self.belly.photo_file = "Belly 2018.jpg"
        self.belly.photo_author = "A. Photographer"
        self.belly.photo_license = "CC BY-SA 3.0"
        self.belly.photo_license_url = "https://creativecommons.org/licenses/by-sa/3.0/"
        self.belly.save()
        show(self.belly, days(3), self.lupo, starttime_override="doors 7pm")
        html = self.page().content.decode()
        self.assertIn('<a href="/bands/belly">Belly</a>', html)
        self.assertIn('<span class="discover-kind">band</span> · Providence, RI', html)
        self.assertIn("Lupo&#x27;s", html)
        self.assertIn("doors 7pm", html)
        self.assertIn("Special:FilePath/Belly_2018.jpg?width=480", html)
        self.assertIn("Photo: A. Photographer", html)
        self.assertNotIn("artist-previews", html)

    def test_the_photo_is_left_for_the_player_when_matched(self):
        self.belly.photo_file = "Belly 2018.jpg"
        self.belly.photo_author = "A. Photographer"
        self.belly.save()
        show(self.belly, days(3), self.lupo)
        spotify("belly")
        with mock.patch.dict(os.environ, SPOTIFY_ON):
            html = self.page().content.decode()
        self.assertNotIn("discover-photo", html)
        self.assertIn("spotify-play", html)

    def test_no_match_and_no_photo(self):
        show(self.anjimile, days(3), self.lupo)
        html = self.page().content.decode()
        self.assertIn('<span class="discover-kind">artist</span> · Boston, MA', html)
        self.assertNotIn("artist-previews", html)
        self.assertNotIn("<figure", html)

    def test_a_show_with_no_venue_and_an_act_with_no_town(self):
        nowhere = Band.objects.create(name="Nowhere Men")
        show(nowhere, days(2))
        html = self.page().content.decode()
        self.assertIn("Venue to be announced", html)
        self.assertIn('<span class="discover-kind">band</span></p>', html)

    def test_more_shows_are_counted(self):
        for n in (2, 4, 6):
            show(self.belly, days(n), self.lupo)
        self.assertContains(self.page(), "+2 more shows")
