import datetime
from unittest import mock

from core.models import Event, SpotifyArtistLink
from core.tests.spotify_fixture import CREDENTIALS
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

Status, Source = SpotifyArtistLink.Status, SpotifyArtistLink.Source


class SpotifyLinkAdminTestCase(TestCase):
    def setUp(self):
        # here rather than on the class, which wouldn't cover setUp's baking
        self.enterContext(mock.patch.dict("os.environ", CREDENTIALS))
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.event = Event.objects.create(
            artists="Epicenter", starttime=timezone.now() + datetime.timedelta(days=2)
        )
        now = timezone.now()
        self.link = SpotifyArtistLink.objects.create(
            name_key="epicenter", status=Status.MATCHED, spotify_artist_id="fakeWrongBand",
            checked_at=now, last_seen_at=now,
        )
        Event.objects.get(pk=self.event.pk).save()  # bake with the wrong match

    def change(self, **data):
        url = reverse("admin:core_spotifyartistlink_change", args=[self.link.pk])
        return self.client.post(url, {"name_key": "Epicenter", **data})

    def baked(self):
        return Event.objects.get(pk=self.event.pk).baked_html_template

    def test_editor_fixes_a_wrong_match(self):
        self.assertIn('data-spotify-artist="fakeWrongBand"', self.baked())
        response = self.change(spotify_link="https://open.spotify.com/artist/abc123?si=x")
        self.assertEqual(response.status_code, 302)
        self.link.refresh_from_db()
        self.assertEqual((self.link.status, self.link.spotify_artist_id, self.link.source), (Status.MATCHED, "abc123", Source.EDITOR))
        self.assertIn('data-spotify-artist="abc123"', self.baked())
        self.assertNotIn("fakeWrongBand", self.baked())

    def test_editor_marks_no_artist(self):
        self.change(no_spotify_artist="on")
        self.link.refresh_from_db()
        self.assertEqual((self.link.status, self.link.spotify_artist_id, self.link.source), (Status.NONE, "", Source.EDITOR))
        self.assertNotIn("spotify-play", self.baked())

    def test_no_artist_action(self):
        self.client.post(
            reverse("admin:core_spotifyartistlink_changelist"),
            {"action": "mark_no_spotify_artist", "_selected_action": [self.link.pk]},
        )
        self.link.refresh_from_db()
        self.assertEqual((self.link.status, self.link.source), (Status.NONE, Source.EDITOR))
        self.assertNotIn("spotify-play", self.baked())

    def test_invalid_url_rejected(self):
        response = self.change(spotify_link="https://example.com/band")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "isn&#x27;t a Spotify artist link")
        self.link.refresh_from_db()
        self.assertEqual((self.link.spotify_artist_id, self.link.source), ("fakeWrongBand", Source.AUTO))

    def test_editor_adds_a_name_not_yet_searched(self):
        response = self.client.post(
            reverse("admin:core_spotifyartistlink_add"),
            {"name_key": "The Ballroom Thieves", "spotify_link": "spotify:artist:fakeBT"},
        )
        self.assertEqual(response.status_code, 302)
        added = SpotifyArtistLink.objects.get(name_key="ballroom thieves")
        self.assertEqual((added.status, added.spotify_artist_id, added.source), (Status.MATCHED, "fakeBT", Source.EDITOR))

    def test_list_filters(self):
        response = self.client.get(reverse("admin:core_spotifyartistlink_changelist"), {"source__exact": "auto"})
        self.assertContains(response, "epicenter")
        response = self.client.get(reverse("admin:core_spotifyartistlink_changelist"), {"status__exact": "none"})
        self.assertNotContains(response, "fakeWrongBand")
