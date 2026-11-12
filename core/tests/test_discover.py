import os
import re
from importlib import import_module
from unittest import mock

from core.artist_previews import act_previews
from core.models import Artist, Band, EventPerformer, MenuItem
from core.saved_shows import COOKIE_NAME, format_saved
from core.tests.apple_music_fixture import SWITCHED_ON as APPLE_ON
from core.tests.discover_fixture import apple, days, show, spotify, venue, youtube
from core.tests.spotify_fixture import CREDENTIALS as SPOTIFY_ON
from core.tests.youtube_fixture import SWITCHED_ON as YOUTUBE_ON
from django.apps import apps as django_apps
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


class WithoutJavaScriptTestCase(DiscoverTestCase):
    def forms_of(self, html):
        return re.findall(r'<form class="save-form" method="post" action="(/saved/toggle/\d+)"><input type="hidden" name="next" value="([^"]*)">', html)

    def test_every_card_lists_its_shows_with_bookmarks_that_return_to_the_card(self):
        events = [show(self.belly, days(n), self.lupo) for n in (3, 5)]
        other = show(self.anjimile, days(4), self.lupo)
        html = self.page().content.decode()
        forms = dict(self.forms_of(html))
        for event, anchor in ((events[0], "bands-belly"), (events[1], "bands-belly"), (other, "artists-anjimile")):
            self.assertEqual(forms[f"/saved/toggle/{event.pk}"], f"/discover#{anchor}-event-{event.pk}")
            self.assertIn(f'id="{anchor}-event-{event.pk}"', html)
        for name in ("Belly", "Anjimile"):
            self.assertIn(f'aria-label="{name}"', html)

    def test_a_show_on_two_cards_has_two_anchors(self):
        artist = Artist.objects.create(name="Belly Solo")
        event = show(self.belly, days(3), self.lupo)
        EventPerformer.objects.create(event=event, artist=artist)
        html = self.page().content.decode()
        nexts = [value for action, value in self.forms_of(html) if action == f"/saved/toggle/{event.pk}"]
        self.assertEqual(sorted(nexts), sorted([
            f"/discover#bands-belly-event-{event.pk}", f"/discover#artists-belly-solo-event-{event.pk}",
        ]))

    def test_a_bookmark_posts_and_returns_to_the_card(self):
        event = show(self.belly, days(3), self.lupo)
        response = self.client.post(
            f"/saved/toggle/{event.pk}", {"next": f"/discover#bands-belly-event-{event.pk}"}
        )
        self.assertRedirects(
            response, f"/discover#bands-belly-event-{event.pk}", fetch_redirect_response=False
        )

    def test_saved_state_comes_from_the_cookie(self):
        saved, unsaved = show(self.belly, days(3), self.lupo), show(self.anjimile, days(4), self.lupo)
        self.client.cookies[COOKIE_NAME] = format_saved([saved.pk])
        html = self.page().content.decode()
        self.assertRegex(html, rf'class="save is-saved" data-event-id="{saved.pk}"')
        self.assertRegex(html, rf'class="save" data-event-id="{unsaved.pk}"')


class MenuTestCase(TestCase):
    def test_the_link_is_in_the_header_and_the_footer(self):
        html = self.client.get("/").content.decode()
        header, footer = html.split('id="footer"') if 'id="footer"' in html else html.split("id='footer'")
        self.assertIn('<a href="/discover">Discover bands</a>', header)
        self.assertIn('<a href="/discover">Discover bands</a>', footer)
        item = MenuItem.objects.get(url="/discover")
        self.assertTrue(item.show_in_header and item.show_in_footer)

    def test_the_migration_adds_one_item_however_often_it_runs(self):
        migration = import_module("core.migrations.0104_discover_menu_item")
        MenuItem.objects.filter(url="/discover").delete()
        migration.add_menu_item(django_apps, None)
        migration.add_menu_item(django_apps, None)
        self.assertEqual(MenuItem.objects.filter(name="Discover bands").count(), 1)
        migration.remove_menu_item(django_apps, None)
        self.assertEqual(MenuItem.objects.filter(url="/discover").count(), 0)


class SiteHeaderTestCase(TestCase):
    def parts(self, path):
        html = self.client.get(path).content.decode()
        header = re.search(r"<div class='header'>.*?id='burgerMenuContents'>.*?</div>", html, re.S).group(0)
        footer = re.search(r"<div id='footer'>.*?</div>", html, re.S).group(0)
        return [re.sub(r"\s+", " ", part) for part in (header, footer)]

    def test_the_masthead_search_and_menus_are_the_home_pages(self):
        home, discover = self.parts("/"), self.parts("/discover")
        self.assertIn("Saved shows", home[0])
        self.assertIn("Discover bands", home[0])
        self.assertIn("site-search", home[0])
        self.assertEqual(home, discover)
        # and the page has no header of its own
        self.assertEqual(self.client.get("/discover").content.decode().count("<header"), 0)


class CardButtonsTestCase(DiscoverTestCase):
    def test_apple_music_only_has_its_button_with_its_icon_and_no_other(self):
        show(self.belly, days(3), self.lupo)
        apple("belly")
        with mock.patch.dict(os.environ, {**SPOTIFY_ON, **APPLE_ON, **YOUTUBE_ON}):
            html = self.page().content.decode()
        self.assertIn('class="apple-play"', html)
        self.assertIn('href="#icon-apple-music"', html)
        self.assertNotIn('class="youtube-play"', html)
        self.assertNotIn('class="spotify-play"', html)
