import datetime
from unittest import mock

from core.models import AppleMusicArtistLink, Event
from core.tests.apple_music_fixture import SWITCHED_ON, FakeAppleMusic, fixture
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

Status, Source = AppleMusicArtistLink.Status, AppleMusicArtistLink.Source


class AppleMusicLinkAdminTestCase(TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict("os.environ", SWITCHED_ON))
        self.apple = FakeAppleMusic(songs={"489634654": fixture("top_songs.json")})
        self.enterContext(mock.patch("core.apple_music.client", lambda: self.apple.client()))
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.event = Event.objects.create(
            artists="Ballroom Thieves", starttime=timezone.now() + datetime.timedelta(days=2)
        )

    def baked(self):
        return Event.objects.get(pk=self.event.pk).baked_html_template

    def test_editor_sets_a_match(self):
        self.assertNotIn("apple-play", self.baked())
        response = self.client.post(
            reverse("admin:core_applemusicartistlink_add"),
            {"name_key": "Ballroom Thieves", "apple_music_link": "https://music.apple.com/us/artist/the-ballroom-thieves/489634654"},
        )
        self.assertEqual(response.status_code, 302)
        link = AppleMusicArtistLink.objects.get(name_key="ballroom thieves")
        self.assertEqual(
            (link.status, link.apple_artist_id, link.top_song_id, link.top_album_id, link.source),
            (Status.MATCHED, "489634654", "964625539", "964625535", Source.EDITOR),
        )
        self.assertEqual(self.apple.song_lookups, ["489634654"])
        self.assertIn('data-apple-artist="489634654"', self.baked())

    def test_invalid_link_rejected(self):
        now = timezone.now()
        link = AppleMusicArtistLink.objects.create(
            name_key="ballroom thieves", status=Status.MATCHED, apple_artist_id="100000077",
            top_song_id="200000001", top_album_id="300000001", checked_at=now, last_seen_at=now,
        )
        response = self.client.post(
            reverse("admin:core_applemusicartistlink_change", args=[link.pk]),
            {"name_key": "Ballroom Thieves", "apple_music_link": "https://open.spotify.com/artist/abc123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "isn&#x27;t an Apple Music artist link")
        link.refresh_from_db()
        self.assertEqual((link.apple_artist_id, link.source), ("100000077", Source.AUTO))

    def test_editor_marks_no_artist(self):
        now = timezone.now()
        link = AppleMusicArtistLink.objects.create(
            name_key="ballroom thieves", status=Status.MATCHED, apple_artist_id="100000077",
            top_song_id="200000001", top_album_id="300000001", checked_at=now, last_seen_at=now,
        )
        Event.objects.get(pk=self.event.pk).save()
        self.assertIn("apple-play", self.baked())
        self.client.post(
            reverse("admin:core_applemusicartistlink_changelist"),
            {"action": "mark_no_apple_music_artist", "_selected_action": [link.pk]},
        )
        link.refresh_from_db()
        self.assertEqual((link.status, link.apple_artist_id, link.source), (Status.NONE, "", Source.EDITOR))
        self.assertNotIn("apple-play", self.baked())

    def test_no_artist_through_the_form(self):
        response = self.client.post(
            reverse("admin:core_applemusicartistlink_add"),
            {"name_key": "Organization Night Band", "no_apple_music_artist": "on"},
        )
        self.assertEqual(response.status_code, 302)
        link = AppleMusicArtistLink.objects.get(name_key="organization night band")
        self.assertEqual((link.status, link.source), (Status.NONE, Source.EDITOR))
        self.assertEqual(self.apple.requests, [])

    def test_list_filters(self):
        response = self.client.get(reverse("admin:core_applemusicartistlink_changelist"), {"source__exact": "auto"})
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("admin:core_applemusicartistlink_changelist"), {"status__exact": "none"})
        self.assertEqual(response.status_code, 200)
