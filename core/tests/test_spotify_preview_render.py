import datetime
from unittest import mock

from core.models import Event, SpotifyArtistLink
from core.tests.spotify_fixture import CREDENTIALS
from django.test import TestCase
from django.utils import timezone


def matched(name_key, artist_id):
    now = timezone.now()
    SpotifyArtistLink.objects.create(
        name_key=name_key, status=SpotifyArtistLink.Status.MATCHED, spotify_artist_id=artist_id,
        checked_at=now, last_seen_at=now,
    )


class PreviewRenderTestCase(TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict("os.environ", CREDENTIALS))
        matched("psymon spine", "fakePsymonSpine")
        matched("lake street dive", "fakeLSD")
        # tomorrow, inside the homepage's three weeks
        self.event = Event.objects.create(
            title="SHEBAD", artists="SHEBAD, Psymon Spine", starttime=timezone.now() + datetime.timedelta(days=1)
        )

    def baked(self, event=None):
        return Event.objects.get(pk=(event or self.event).pk).baked_html_template

    def test_button_for_a_matched_artist_only(self):
        html = self.baked()
        self.assertEqual(html.count('class="spotify-play"'), 1)
        self.assertIn('href="https://open.spotify.com/artist/fakePsymonSpine"', html)
        self.assertIn('data-spotify-artist="fakePsymonSpine"', html)
        self.assertIn("▶ Psymon Spine", html)
        self.assertNotIn("▶ SHEBAD", html)

    def test_buttons_in_a_row_of_their_own_below_the_text(self):
        html = self.baked()
        row = html.index('<div class="spotify-artists">')
        # after the text and its ical/gcal/share links, and the tix column, not inside them
        self.assertGreater(row, html.index('class="share"'))
        self.assertGreater(row, html.index('<div class="event-ticket">'))
        self.assertNotIn("spotify-play", html[html.index('<span class="event-content">') : row])

    def test_buttons_in_the_order_the_names_appear(self):
        matched("shebad", "fakeShebad")
        event = Event.objects.create(
            title="SHEBAD", artists="Lake Street Dive, Psymon Spine",
            starttime=timezone.now() + datetime.timedelta(days=1),
        )
        html = self.baked(event)
        self.assertLess(html.index("fakeShebad"), html.index("fakeLSD"))
        self.assertLess(html.index("fakeLSD"), html.index("fakePsymonSpine"))

    def test_duo_gets_a_button_per_matched_act(self):
        matched("boulder canyon", "fakeBoulder")
        event = Event.objects.create(
            title="Chris Collins & Boulder Canyon", starttime=timezone.now() + datetime.timedelta(days=1)
        )
        html = self.baked(event)
        self.assertEqual(html.count('class="spotify-play"'), 1)
        self.assertIn("▶ Boulder Canyon", html)

    def test_occasion_labelled_with_the_artists_part_of_the_name(self):
        matched("buffalo tom", "fakeBT")
        event = Event.objects.create(
            title="BUFFALO TOM 3rd Annual charity concert", starttime=timezone.now() + datetime.timedelta(days=1)
        )
        html = self.baked(event)
        self.assertIn('data-spotify-artist="fakeBT"', html)
        self.assertIn("▶ BUFFALO TOM\n", html)

    def test_one_button_per_artist(self):
        matched("dark star orchestra", "fakeDSO")
        event = Event.objects.create(
            title="Dark Star Orchestra - Celebrating 45 Years", artists="Dark Star Orchestra",
            starttime=timezone.now() + datetime.timedelta(days=1),
        )
        self.assertEqual(self.baked(event).count('data-spotify-artist="fakeDSO"'), 1)

    def test_ambiguous_and_none_names_get_no_button(self):
        now = timezone.now()
        for key, status in (("shebad", SpotifyArtistLink.Status.AMBIGUOUS), ("dyr faser", SpotifyArtistLink.Status.NONE)):
            SpotifyArtistLink.objects.create(name_key=key, status=status, checked_at=now, last_seen_at=now)
        event = Event.objects.create(artists="SHEBAD, Dyr Faser", starttime=now + datetime.timedelta(days=1))
        self.assertNotIn("spotify-play", self.baked(event))

    def test_homepage_has_buttons_but_no_player(self):
        response = self.client.get("/")
        self.assertContains(response, 'data-spotify-artist="fakePsymonSpine"')
        self.assertContains(response, "core/js/spotify_preview.js")
        self.assertNotContains(response, "<iframe")
        self.assertNotContains(response, "open.spotify.com/embed")

    def test_nothing_rendered_when_not_configured(self):
        with mock.patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "", "SPOTIFY_CLIENT_SECRET": ""}):
            self.event.save()
        self.assertNotIn("spotify", self.baked())
