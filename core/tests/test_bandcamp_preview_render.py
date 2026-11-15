import datetime
import os
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from core import bandcamp_embeds
from core.artist_previews import ORDERS, players_in_order
from core.event_performers import link_from_names
from core.models import Artist, Band, Event, EventPerformer
from core.tests.apple_music_fixture import SWITCHED_ON as APPLE_ON
from core.tests.spotify_fixture import CREDENTIALS
from core.tests.test_apple_music_preview_render import apple_link, spotify_link
from core.tests.test_bandcamp_embeds import FakeSession, page, player
from core.tests.youtube_fixture import SWITCHED_ON as YOUTUBE_ON
from core.tests.test_youtube_preview_render import youtube_link

KRILL = "https://krill.bandcamp.com/"
SERVICE_SETTINGS = ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "APPLE_MUSIC_PREVIEWS", "YOUTUBE_PREVIEWS", "YOUTUBE_API_KEY")


def found_band(name="Krill", url=KRILL, **fields):
    values = dict(
        bandcamp_url=url, bandcamp_embed_kind="album", bandcamp_embed_id="111", bandcamp_embed_status="found",
        bandcamp_embed_for=url, bandcamp_embed_checked_at=timezone.now(),
    )
    return Band.objects.create(name=name, **{**values, **fields})


def listed(artists="Krill", *acts, hours=24):
    """an event with its performers linked, baked again so it shows them; returns its stored html"""
    event = Event.objects.create(artists=artists, starttime=timezone.now() + datetime.timedelta(hours=hours))
    for order, act in enumerate(acts):
        EventPerformer.objects.create(event=event, order=order, **{"band" if isinstance(act, Band) else "artist": act})
    event.save()
    return Event.objects.get(pk=event.pk).baked_html_template


class BandcampButtonTestCase(TestCase):
    def setUp(self):
        # whatever the machine has set, no other service is on unless a test says so
        environ = {name: "" for name in SERVICE_SETTINGS}
        self.enterContext(mock.patch.dict(os.environ, environ))

    def test_event_row_with_a_player(self):
        self.enterContext(mock.patch.dict(os.environ, {**CREDENTIALS, **APPLE_ON, **YOUTUBE_ON}))
        spotify_link("krill", "fakeKrill")
        apple_link("krill", "489634654")
        youtube_link("krill", "abc123DEF45")
        html = listed("Krill", found_band())
        row = html[html.index('<div class="artist-previews">'):]
        order = [row.index(f'class="{c}-play"') for c in ("spotify", "apple", "youtube", "bandcamp")]
        self.assertEqual(order, sorted(order))
        # one entry: all four buttons are Krill's
        self.assertEqual(row.count("▶ Krill"), 4)

    def test_the_button_is_a_plain_link_to_the_acts_page(self):
        html = listed("Krill", found_band())
        self.assertIn(f'href="{KRILL}"', html)
        self.assertIn('data-bandcamp-kind="album"', html)
        self.assertIn('data-bandcamp-id="111"', html)
        self.assertIn('title="Listen to Krill on Bandcamp"', html)
        self.assertIn('target="_blank"', html[html.index("bandcamp-play"):])

    def test_only_bandcamp(self):
        html = listed("Krill", found_band())
        row = html[html.index('<div class="artist-previews">'):]
        self.assertIn('class="bandcamp-play"', row)
        for other in ("spotify", "apple", "youtube"):
            self.assertNotIn(f'class="{other}-play"', row)

    def test_no_other_service_configured(self):
        # all three previews are off (setUp), and the event's row still shows the button
        self.assertIn("bandcamp-play", listed("Krill", found_band()))

    def test_acts_on_one_bill_keep_their_billing_order(self):
        krill, pile = found_band("Krill"), found_band("Pile", "https://pile.bandcamp.com/", bandcamp_embed_id="222")
        html = listed("Pile, Krill", pile, krill)
        self.assertLess(html.index("▶ Pile on Bandcamp"), html.index("▶ Krill on Bandcamp"))

    def test_an_artist_as_well_as_a_band(self):
        solo = Artist.objects.create(
            name="Solo", bandcamp_url="https://solo.bandcamp.com/", bandcamp_embed_kind="track", bandcamp_embed_id="9",
            bandcamp_embed_status="found", bandcamp_embed_for="https://solo.bandcamp.com/",
        )
        html = listed("Solo", solo)
        self.assertIn('data-bandcamp-kind="track"', html)

    def test_an_editors_player_without_an_address_links_to_the_player(self):
        band = Band.objects.create(
            name="Krill", bandcamp_embed_kind="album", bandcamp_embed_id="7", field_sources={"bandcamp_embed": "editor"}
        )
        html = listed("Krill", band)
        self.assertIn('href="https://bandcamp.com/EmbeddedPlayer/album=7/', html)
        self.assertIn('data-bandcamp-page=""', html)

    def test_act_with_no_usable_player(self):
        cases = {
            "no playable": found_band("A", "https://a.bandcamp.com/", bandcamp_embed_status="no_playable", bandcamp_embed_kind="", bandcamp_embed_id=""),
            "held for review": found_band("B", "https://b.bandcamp.com/", needs_review=True),
            "changed address": found_band("C", "https://c.bandcamp.com/", bandcamp_embed_for="https://old.bandcamp.com/"),
            "declined": found_band("D", "https://d.bandcamp.com/", bandcamp_embed_status="declined"),
            "no id": found_band("E", "https://e.bandcamp.com/", bandcamp_embed_id=""),
        }
        for label, band in cases.items():
            with self.subTest(label):
                self.assertNotIn("bandcamp-play", listed(band.name, band))

    def test_an_act_the_event_isnt_linked_to_has_no_button(self):
        found_band()
        self.assertNotIn("bandcamp-play", listed("Krill"))

    def test_nothing_loads_until_pressed(self):
        listed("Krill", found_band())
        homepage = self.client.get("/").content.decode()
        self.assertIn("bandcamp-play", homepage)
        self.assertNotIn("<iframe", homepage)
        self.assertNotIn("EmbeddedPlayer", homepage)

    def test_no_query_per_page_view(self):
        listed("Krill", found_band())
        with mock.patch("requests.Session.request", side_effect=AssertionError("no requests")) as request:
            self.client.get("/")
        request.assert_not_called()


class BandcampEventsReRenderedTestCase(TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict(os.environ, {name: "" for name in SERVICE_SETTINGS}))

    def stored(self, event):
        return Event.objects.get(pk=event.pk).baked_html_template

    def test_the_lookup_finding_a_player_adds_the_button(self):
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        html = listed("Krill", band)
        event = Event.objects.get()
        self.assertNotIn("bandcamp-play", html)
        session = FakeSession({KRILL: page("album_redirect.html"), player("album", "111"): page("player_available.html")})
        with mock.patch.object(bandcamp_embeds.requests, "Session", return_value=session), mock.patch.object(
            bandcamp_embeds.time, "sleep"
        ):
            call_command("find_bandcamp_embeds", stdout=StringIO())
        self.assertIn('data-bandcamp-id="111"', self.stored(event))

    def test_an_editors_change_updates_the_button(self):
        from django.contrib.auth.models import User
        from django.urls import reverse
        from core.tests.test_admin_bandcamp_player import form_data

        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        band = Band.objects.create(name="Krill", bandcamp_url=KRILL)
        listed("Krill", band)
        event = Event.objects.get()
        url = reverse("admin:core_band_change", args=[band.pk])
        self.client.post(url, form_data(band, bandcamp_embed_kind="album", bandcamp_embed_id="777"))
        self.assertIn('data-bandcamp-id="777"', self.stored(event))
        # and a changed address drops a found player's button at once
        band = found_band("Pile", "https://pile.bandcamp.com/")
        listed("Pile", band)
        pile_event = Event.objects.get(artists="Pile")
        self.client.post(reverse("admin:core_band_change", args=[band.pk]), form_data(band, bandcamp_url="https://piles.bandcamp.com/", bandcamp_embed_kind="album", bandcamp_embed_id="111"))
        # kind and id are unchanged by the form, but the player is no longer usable
        self.assertNotIn("bandcamp-play", self.stored(pile_event))

    def test_declining_removes_the_button(self):
        from django.contrib.auth.models import User
        from django.urls import reverse

        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        band = found_band()
        listed("Krill", band)
        event = Event.objects.get()
        self.assertIn("bandcamp-play", self.stored(event))
        self.client.post(reverse("admin:core_band_changelist"), {"action": "decline_bandcamp_player", "_selected_action": [band.pk]})
        self.assertNotIn("bandcamp-play", self.stored(event))

    def test_performer_links_rebuilt_to_include_a_band_with_a_player(self):
        found_band()
        event = Event.objects.create(artists="Krill", starttime=timezone.now() + datetime.timedelta(days=1))
        self.assertNotIn("bandcamp-play", self.stored(event))
        link_from_names(event)
        self.assertIn("bandcamp-play", self.stored(event))

    def test_deleting_the_band_drops_the_button(self):
        band = found_band()
        listed("Krill", band)
        event = Event.objects.get()
        band.delete()
        self.assertNotIn("bandcamp-play", self.stored(event))

    def test_marking_ready_shows_the_button(self):
        from django.contrib.auth.models import User
        from django.urls import reverse

        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        band = found_band(needs_review=True, review_reasons=["not_found"])
        listed("Krill", band)
        event = Event.objects.get()
        self.assertNotIn("bandcamp-play", self.stored(event))
        self.client.post(reverse("admin:core_band_changelist"), {"action": "mark_ready", "_selected_action": [band.pk]})
        self.assertIn("bandcamp-play", self.stored(event))


class PlayerOrderTestCase(SimpleTestCase):
    FULL = {"label": "Krill", "spotify": "s", "apple": {"artist": "a"}, "youtube": {"video": "v"}, "bandcamp": {"id": "1"}}

    def services(self, entry, screen):
        return [service for service, _ in players_in_order(entry, screen)]

    def test_deck_order(self):
        entry = {"label": "Krill", "spotify": "s", "bandcamp": {"id": "1"}}
        self.assertEqual(self.services(entry, "deck"), ["spotify", "bandcamp"])

    def test_full_order(self):
        self.assertEqual(self.services(self.FULL, "deck"), ["youtube", "apple", "spotify", "bandcamp"])
        self.assertEqual(self.services(self.FULL, "event"), ["spotify", "apple", "youtube", "bandcamp"])

    def test_only_bandcamp_in_the_deck(self):
        self.assertEqual(players_in_order({"label": "Krill", "bandcamp": {"id": "1"}, "spotify": None}, "deck"), [("bandcamp", {"id": "1"})])

    def test_bandcamp_is_last_on_every_screen(self):
        self.assertEqual({order[-1] for order in ORDERS.values()}, {"bandcamp"})

    def test_an_act_with_nothing(self):
        self.assertEqual(players_in_order({"label": "Krill"}, "deck"), [])

    def test_the_event_order_matches_the_rows_html(self):
        # the template draws buttons in this order: event.html
        from pathlib import Path

        html = (Path(__file__).resolve().parents[1] / "templates" / "core" / "event.html").read_text()
        positions = [html.index(f'class="{c}-play"') for c in ("spotify", "apple", "youtube", "bandcamp")]
        self.assertEqual(positions, sorted(positions))
