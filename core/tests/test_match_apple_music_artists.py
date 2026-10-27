import datetime
from io import StringIO
from unittest import mock

from core.models import AppleMusicArtistLink, Event, JobRun
from core.tests.apple_music_fixture import (
    SWITCHED_ON,
    FakeAppleMusic,
    artists,
    fixture,
    rate_limited,
    response,
    top_songs,
)
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

Status, Source = AppleMusicArtistLink.Status, AppleMusicArtistLink.Source
BALLROOM = {"The Ballroom Thieves": fixture("search_unique.json")}
BALLROOM_SONGS = {"489634654": fixture("top_songs.json")}


def upcoming_event(title=None, artists=None, days=3, **fields):
    return Event.objects.create(
        title=title, artists=artists, starttime=timezone.now() + datetime.timedelta(days=days), **fields
    )


def link(name_key, days_ago=0, **fields):
    when = timezone.now() - datetime.timedelta(days=days_ago)
    defaults = {
        "status": Status.MATCHED, "apple_artist_id": "100000077", "top_song_id": "200000001",
        "top_album_id": "300000001", "checked_at": when, "last_seen_at": when,
    }
    return AppleMusicArtistLink.objects.create(name_key=name_key, **{**defaults, **fields})


class CommandTestCase(TestCase):
    def setUp(self):
        # here rather than on the class, so setUp's events bake with apple music on
        self.enterContext(mock.patch.dict("os.environ", SWITCHED_ON))

    def run_command(self, apple, *args):
        out = StringIO()
        with apple.patch():
            call_command("match_apple_music_artists", *args, stdout=out)
        return out.getvalue()


class MatchingTestCase(CommandTestCase):
    def test_unique_exact_match_with_its_top_song(self):
        upcoming_event(artists="The Ballroom Thieves")
        apple = FakeAppleMusic(BALLROOM, BALLROOM_SONGS)
        self.run_command(apple)
        found = AppleMusicArtistLink.objects.get(name_key="ballroom thieves")
        self.assertEqual(
            (found.status, found.apple_artist_id, found.top_song_id, found.top_album_id, found.source),
            (Status.MATCHED, "489634654", "964625539", "964625535", Source.AUTO),
        )

    def test_two_artists_with_the_same_name(self):
        upcoming_event(artists="Epicenter")
        apple = FakeAppleMusic({"Epicenter": fixture("search_same_name.json")})
        self.run_command(apple)
        found = AppleMusicArtistLink.objects.get(name_key="epicenter")
        self.assertEqual((found.status, found.apple_artist_id), (Status.AMBIGUOUS, ""))
        self.assertEqual(apple.song_lookups, [])

    def test_no_exact_match(self):
        upcoming_event(artists="Haven's Den")
        self.run_command(FakeAppleMusic({"Haven's Den": fixture("search_no_exact.json")}))
        self.assertEqual(AppleMusicArtistLink.objects.get(name_key="havens den").status, Status.NOT_FOUND)

    def test_same_name_on_many_events_searched_once(self):
        for days in range(1, 4):
            upcoming_event(artists="Lake Street Dive", days=days)
        apple = FakeAppleMusic()
        self.run_command(apple)
        self.assertEqual(apple.searches, ["Lake Street Dive"])

    def test_no_top_songs(self):
        upcoming_event(artists="Quiet Band")
        apple = FakeAppleMusic({"Quiet Band": artists(("Quiet Band", "100000099"))})
        self.run_command(apple)
        found = AppleMusicArtistLink.objects.get(name_key="quiet band")
        self.assertEqual((found.status, found.top_song_id, found.top_album_id), (Status.MATCHED, "", ""))

    def test_dry_run_saves_nothing(self):
        upcoming_event(artists="The Ballroom Thieves")
        out = self.run_command(FakeAppleMusic(BALLROOM, BALLROOM_SONGS), "--dry-run")
        self.assertIn("The Ballroom Thieves: matched -> 489634654, top song 964625539 on album 964625535", out)
        self.assertFalse(AppleMusicArtistLink.objects.exists())

    def test_names_and_limit(self):
        upcoming_event(artists="Arto Vaun, Shadow Monster, Dyr Faser")
        apple = FakeAppleMusic()
        self.run_command(apple, "--names", "Shadow Monster,Dyr Faser", "--limit", "1")
        self.assertEqual(apple.searches, ["Dyr Faser"])

    def test_not_configured(self):
        upcoming_event(artists="The Ballroom Thieves")
        apple = FakeAppleMusic()
        with mock.patch.dict("os.environ", {"APPLE_MUSIC_PRIVATE_KEY": ""}):
            out = self.run_command(apple)
        self.assertIn("apple music isn't configured", out)
        self.assertEqual(apple.requests, [])
        self.assertFalse(AppleMusicArtistLink.objects.exists())


class RefreshTestCase(CommandTestCase):
    def test_refresh_after_30_days(self):
        upcoming_event(artists="The Ballroom Thieves")
        old = link("ballroom thieves", days_ago=31)
        self.run_command(FakeAppleMusic(BALLROOM, BALLROOM_SONGS))
        old.refresh_from_db()
        self.assertEqual((old.apple_artist_id, old.top_song_id), ("489634654", "964625539"))
        self.assertGreater(old.checked_at, timezone.now() - datetime.timedelta(minutes=1))

    def test_recent_link_not_rechecked(self):
        upcoming_event(artists="The Ballroom Thieves")
        link("ballroom thieves", days_ago=29)
        apple = FakeAppleMusic()
        self.run_command(apple)
        self.assertEqual(apple.requests, [])

    def test_editors_match_keeps_its_artist_but_gets_a_new_top_song(self):
        upcoming_event(artists="Ballroom Thieves")
        old = link("ballroom thieves", days_ago=31, source=Source.EDITOR, apple_artist_id="489634654")
        apple = FakeAppleMusic(songs={"489634654": top_songs("200000009", "300000009")})
        self.run_command(apple)
        old.refresh_from_db()
        self.assertEqual(apple.searches, [])
        self.assertEqual(
            (old.apple_artist_id, old.top_song_id, old.top_album_id, old.source),
            ("489634654", "200000009", "300000009", Source.EDITOR),
        )

    def test_editors_no_artist_never_searched(self):
        upcoming_event(artists="Organization Night Band")
        link("organization night band", days_ago=60, source=Source.EDITOR, status=Status.NONE, apple_artist_id="")
        apple = FakeAppleMusic()
        self.run_command(apple)
        self.assertEqual(apple.requests, [])

    def test_link_no_longer_needed(self):
        link("gone band", days_ago=31)
        link("recent band", days_ago=10)
        self.run_command(FakeAppleMusic())
        self.assertEqual(list(AppleMusicArtistLink.objects.values_list("name_key", flat=True)), ["recent band"])

    def test_changed_song_rerendered(self):
        events = [upcoming_event(artists="The Ballroom Thieves", days=days) for days in (1, 2)]
        link("ballroom thieves", days_ago=31, apple_artist_id="489634654")
        for event in events:
            event.save()  # baked with the old song
            self.assertIn('data-apple-song="200000001"', Event.objects.get(pk=event.pk).baked_html_template)
        self.run_command(FakeAppleMusic(BALLROOM, BALLROOM_SONGS))
        for event in events:
            html = Event.objects.get(pk=event.pk).baked_html_template
            self.assertIn('data-apple-song="964625539" data-apple-album="964625535"', html)
            self.assertNotIn("200000001", html)

    def test_nothing_else_stored(self):
        upcoming_event(artists="The Ballroom Thieves")
        self.run_command(FakeAppleMusic(BALLROOM, BALLROOM_SONGS))
        row = AppleMusicArtistLink.objects.values().get()
        self.assertEqual(
            set(row),
            {"id", "name_key", "status", "apple_artist_id", "top_song_id", "top_album_id", "source",
             "checked_at", "last_seen_at"},
        )
        self.assertNotIn("Archers", str(row))


class RateLimitTestCase(CommandTestCase):
    def test_rate_limited_then_succeeds(self):
        upcoming_event(artists="The Ballroom Thieves")
        apple = FakeAppleMusic(
            {"The Ballroom Thieves": [rate_limited(3), response(200, fixture("search_unique.json"))]}, BALLROOM_SONGS
        )
        self.run_command(apple)
        self.assertIn(3.0, apple.sleeps)
        self.assertEqual(AppleMusicArtistLink.objects.get().status, Status.MATCHED)

    def test_persistent_failure(self):
        upcoming_event(artists="Epicenter, The Ballroom Thieves")
        old = link("epicenter", days_ago=31)
        apple = FakeAppleMusic(
            {"Epicenter": [rate_limited(), rate_limited(), rate_limited()], **BALLROOM}, BALLROOM_SONGS
        )
        out = self.run_command(apple)
        old.refresh_from_db()
        self.assertEqual(old.apple_artist_id, "100000077")
        self.assertIn("Epicenter: failed", out)
        self.assertTrue(AppleMusicArtistLink.objects.filter(name_key="ballroom thieves").exists())

    def test_blocked_for_hours(self):
        event = upcoming_event(artists="Arto Vaun, The Ballroom Thieves, Shadow Monster")
        apple = FakeAppleMusic(
            {"Arto Vaun": artists(("Arto Vaun", "100000031")), "The Ballroom Thieves": [rate_limited(86400)]},
            {"100000031": top_songs("200000031", "300000031")},
        )
        out = self.run_command(apple)
        self.assertNotIn(86400.0, apple.sleeps)
        self.assertEqual(apple.searches, ["Arto Vaun", "The Ballroom Thieves"])
        self.assertIn('data-apple-song="200000031"', Event.objects.get(pk=event.pk).baked_html_template)
        self.assertIn("stopped early, 1 names left", out)
        summary = dict(JobRun.objects.get(command="match_apple_music_artists").summary)
        self.assertEqual((summary["searched"], summary["failed"], summary["left for the next run"]), (2, 1, 1))

    def test_bad_credentials_stop_the_run(self):
        upcoming_event(artists="Arto Vaun, The Ballroom Thieves")
        apple = FakeAppleMusic({"Arto Vaun": [response(401, fixture("unauthorized.json"))] * 5})
        with self.assertRaises(CommandError) as raised:
            self.run_command(apple)
        self.assertIn("credentials were rejected", str(raised.exception))
        # tried five times, then stopped
        self.assertEqual(apple.searches, ["Arto Vaun"] * 5)
        self.assertFalse(AppleMusicArtistLink.objects.exists())

    def test_throttled(self):
        upcoming_event(artists="Arto Vaun, Shadow Monster")
        apple = FakeAppleMusic()
        self.run_command(apple)
        self.assertEqual(len(apple.searches), 2)
        self.assertIn(0.5, apple.sleeps)

    def test_job_summary(self):
        upcoming_event(artists="The Ballroom Thieves, Epicenter, Haven's Den")
        link("old one", days_ago=40)
        apple = FakeAppleMusic(
            {**BALLROOM, "Epicenter": fixture("search_same_name.json"), "Haven's Den": fixture("search_no_exact.json")},
            BALLROOM_SONGS,
        )
        self.run_command(apple)
        self.assertEqual(
            JobRun.objects.get(command="match_apple_music_artists").summary,
            [["searched", 3], ["matched", 1], ["ambiguous", 1], ["not found", 1], ["deleted", 1], ["failed", 0],
             ["left for the next run", 0]],
        )
