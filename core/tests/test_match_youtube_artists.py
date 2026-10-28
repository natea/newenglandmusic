import datetime
from io import StringIO
from unittest import mock

from core.models import AppleMusicArtistLink, Event, JobRun, SpotifyArtistLink, YouTubeArtistLink
from core.tests import apple_music_fixture
from core.tests.apple_music_fixture import FakeAppleMusic
from core.tests.youtube_fixture import (
    BALLROOM_SPOTIFY,
    BALLROOM_TOPIC,
    BALLROOM_VIDEO,
    CONFIGURED,
    DINOSAUR_CHANNEL,
    DINOSAUR_SPOTIFY,
    SWITCHED_ON,
    FakeWeb,
    quota_exceeded,
    topic_description,
    video,
)
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

Status, Evidence, Source = YouTubeArtistLink.Status, YouTubeArtistLink.Evidence, YouTubeArtistLink.Source
BALLROOM_APPLE = "489634654"
BALLROOM_SONGS = {BALLROOM_APPLE: apple_music_fixture.fixture("top_songs.json")}
BALLROOM_QUERY = "The Ballroom Thieves Archers"


def upcoming_event(artists, days=3, **fields):
    return Event.objects.create(artists=artists, starttime=timezone.now() + datetime.timedelta(days=days), **fields)


def when(days_ago=0):
    return timezone.now() - datetime.timedelta(days=days_ago)


def spotify(name_key, artist_id):
    return SpotifyArtistLink.objects.create(
        name_key=name_key, status=SpotifyArtistLink.Status.MATCHED, spotify_artist_id=artist_id,
        checked_at=when(), last_seen_at=when(),
    )


def apple(name_key, artist_id, song="964625539", album="964625535"):
    return AppleMusicArtistLink.objects.create(
        name_key=name_key, status=AppleMusicArtistLink.Status.MATCHED, apple_artist_id=artist_id,
        top_song_id=song, top_album_id=album, checked_at=when(), last_seen_at=when(),
    )


def link(name_key, days_ago=0, **fields):
    defaults = {
        "status": Status.MATCHED, "evidence": Evidence.TOPIC_SONG, "channel_id": BALLROOM_TOPIC,
        "video_id": BALLROOM_VIDEO, "checked_at": when(days_ago), "last_seen_at": when(days_ago),
    }
    return YouTubeArtistLink.objects.create(name_key=name_key, **{**defaults, **fields})


def topic_video(video_id=BALLROOM_VIDEO, embeddable=True):
    return video(
        video_id, BALLROOM_TOPIC, "The Ballroom Thieves - Topic", "Archers",
        topic_description("Archers", "The Ballroom Thieves", "A Wolf in the Doorway"), embeddable,
    )


class CommandTestCase(TestCase):
    def setUp(self):
        self.enterContext(mock.patch.dict("os.environ", {**SWITCHED_ON, **apple_music_fixture.CREDENTIALS}))
        self.apple = FakeAppleMusic(songs=BALLROOM_SONGS)

    def run_command(self, web, *args):
        out = StringIO()
        with web.patch(), self.apple.patch("core.management.commands.match_youtube_artists.AppleMusicClient"):
            call_command("match_youtube_artists", *args, stdout=out)
        return out.getvalue()

    def ballroom(self):
        upcoming_event("The Ballroom Thieves")
        apple("ballroom thieves", BALLROOM_APPLE)


class ConsideredTestCase(CommandTestCase):
    def test_not_configured(self):
        upcoming_event("The Ballroom Thieves")
        web = FakeWeb()
        with mock.patch.dict("os.environ", {"YOUTUBE_API_KEY": ""}):
            out = self.run_command(web)
        self.assertIn("isn't configured", out)
        self.assertEqual(web.requests, [])
        self.assertEqual(YouTubeArtistLink.objects.count(), 0)

    def test_unmatched_name_skipped(self):
        upcoming_event("DJ Maltese")
        SpotifyArtistLink.objects.create(
            name_key="dj maltese", status=SpotifyArtistLink.Status.AMBIGUOUS, checked_at=when(), last_seen_at=when()
        )
        web = FakeWeb()
        self.run_command(web)
        self.assertEqual(web.requests, [])
        self.assertEqual(YouTubeArtistLink.objects.count(), 0)

    def test_dry_run(self):
        self.ballroom()
        web = FakeWeb(searches={BALLROOM_QUERY: [BALLROOM_VIDEO]}, videos={BALLROOM_VIDEO: topic_video()})
        out = self.run_command(web, "--dry-run")
        self.assertIn(f"The Ballroom Thieves: matched by topic song -> {BALLROOM_VIDEO}", out)
        self.assertEqual(YouTubeArtistLink.objects.count(), 0)


class IdLinkTestCase(CommandTestCase):
    def test_wikidata_link(self):
        upcoming_event("Dinosaur Jr.")
        spotify("dinosaur jr", DINOSAUR_SPOTIFY)
        web = FakeWeb(wikidata={("P1902", DINOSAUR_SPOTIFY): [DINOSAUR_CHANNEL]}, channels={DINOSAUR_CHANNEL})
        self.run_command(web)
        found = YouTubeArtistLink.objects.get(name_key="dinosaur jr")
        self.assertEqual(
            (found.status, found.evidence, found.channel_id, found.video_id, found.source),
            (Status.MATCHED, Evidence.WIKIDATA, DINOSAUR_CHANNEL, "", Source.AUTO),
        )
        self.assertEqual(web.search_queries, [])

    def test_musicbrainz_link(self):
        upcoming_event("Dinosaur Jr.")
        spotify("dinosaur jr", DINOSAUR_SPOTIFY)
        web = FakeWeb(musicbrainz={DINOSAUR_SPOTIFY: [f"https://www.youtube.com/channel/{DINOSAUR_CHANNEL}"]}, channels={DINOSAUR_CHANNEL})
        self.run_command(web)
        found = YouTubeArtistLink.objects.get(name_key="dinosaur jr")
        self.assertEqual((found.status, found.evidence, found.channel_id), (Status.MATCHED, Evidence.MUSICBRAINZ, DINOSAUR_CHANNEL))

    def test_sources_disagree(self):
        upcoming_event("Dinosaur Jr.")
        spotify("dinosaur jr", DINOSAUR_SPOTIFY)
        other = "UCsomeoneElseEntirely0001"[:24]
        web = FakeWeb(
            wikidata={("P1902", DINOSAUR_SPOTIFY): [DINOSAUR_CHANNEL]},
            musicbrainz={DINOSAUR_SPOTIFY: [f"https://www.youtube.com/channel/{other}"]},
            channels={DINOSAUR_CHANNEL, other},
        )
        self.run_command(web)
        found = YouTubeArtistLink.objects.get(name_key="dinosaur jr")
        self.assertEqual((found.status, found.channel_id), (Status.AMBIGUOUS, ""))

    def test_channel_both_sources_give_stands(self):
        upcoming_event("Dinosaur Jr.")
        spotify("dinosaur jr", DINOSAUR_SPOTIFY)
        second = "UCdinosaurJrSecondChan01"
        web = FakeWeb(
            wikidata={("P1902", DINOSAUR_SPOTIFY): [DINOSAUR_CHANNEL]},
            musicbrainz={DINOSAUR_SPOTIFY: [f"https://www.youtube.com/channel/{c}" for c in (DINOSAUR_CHANNEL, second)]},
            channels={DINOSAUR_CHANNEL, second},
        )
        self.run_command(web)
        found = YouTubeArtistLink.objects.get(name_key="dinosaur jr")
        self.assertEqual((found.status, found.channel_id), (Status.MATCHED, DINOSAUR_CHANNEL))

    def test_musicbrainz_down_carries_on_with_wikidata(self):
        upcoming_event("Dinosaur Jr.")
        spotify("dinosaur jr", DINOSAUR_SPOTIFY)
        upcoming_event("Lake Street Dive")
        spotify("lake street dive", "LakeStreetDiveSpotify1")
        web = FakeWeb(wikidata={("P1902", DINOSAUR_SPOTIFY): [DINOSAUR_CHANNEL]}, channels={DINOSAUR_CHANNEL}, musicbrainz_503s=100)
        out = self.run_command(web)
        self.assertIn("carrying on without musicbrainz", out)
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="dinosaur jr").status, Status.MATCHED)
        # asked only until it gave up
        self.assertEqual(len([r for r in web.requests if "musicbrainz" in r.url]), 4)

    def test_rejected_key_stops_the_run(self):
        upcoming_event("Dinosaur Jr.")
        spotify("dinosaur jr", DINOSAUR_SPOTIFY)
        upcoming_event("Lake Street Dive")
        spotify("lake street dive", "LakeStreetDiveSpotify1")
        web = FakeWeb(
            wikidata={("P1902", DINOSAUR_SPOTIFY): [DINOSAUR_CHANNEL], ("P1902", "LakeStreetDiveSpotify1"): [BALLROOM_TOPIC]},
            forbidden=True,
        )
        with self.assertRaises(CommandError) as raised:
            self.run_command(web)
        # one refused request, not one per name
        self.assertEqual(len(web.youtube_requests), 1)
        self.assertIn("refused YOUTUBE_API_KEY", str(raised.exception))
        self.assertEqual(YouTubeArtistLink.objects.count(), 0)

    def test_deleted_channel_falls_through(self):
        upcoming_event("Dinosaur Jr.")
        spotify("dinosaur jr", DINOSAUR_SPOTIFY)
        web = FakeWeb(wikidata={("P1902", DINOSAUR_SPOTIFY): [DINOSAUR_CHANNEL]})
        self.run_command(web)
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="dinosaur jr").status, Status.NOT_FOUND)

    def test_spotify_only_artist_with_no_id_link(self):
        upcoming_event("Dinosaur Jr.")
        spotify("dinosaur jr", DINOSAUR_SPOTIFY)
        web = FakeWeb()
        self.run_command(web)
        self.assertEqual(web.search_queries, [])
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="dinosaur jr").status, Status.NOT_FOUND)


class SongTestCase(CommandTestCase):
    def test_topic_channel_recording(self):
        self.ballroom()
        web = FakeWeb(searches={BALLROOM_QUERY: [BALLROOM_VIDEO]}, videos={BALLROOM_VIDEO: topic_video()})
        self.run_command(web)
        found = YouTubeArtistLink.objects.get(name_key="ballroom thieves")
        self.assertEqual(
            (found.status, found.evidence, found.video_id, found.channel_id),
            (Status.MATCHED, Evidence.TOPIC_SONG, BALLROOM_VIDEO, BALLROOM_TOPIC),
        )

    def test_topic_preferred_over_the_artist_channel(self):
        self.ballroom()
        own = video("own00000001", "UCBallroomThievesOwn0001", "The Ballroom Thieves", "The Ballroom Thieves - Archers (Official Video)")
        web = FakeWeb(searches={BALLROOM_QUERY: ["own00000001", BALLROOM_VIDEO]}, videos={"own00000001": own, BALLROOM_VIDEO: topic_video()})
        self.run_command(web)
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="ballroom thieves").video_id, BALLROOM_VIDEO)

    def test_artist_channel_recording(self):
        self.ballroom()
        own = video("own00000001", "UCBallroomThievesOwn0001", "The Ballroom Thieves", "The Ballroom Thieves - Archers (Official Video)")
        web = FakeWeb(searches={BALLROOM_QUERY: ["own00000001"]}, videos={"own00000001": own})
        self.run_command(web)
        found = YouTubeArtistLink.objects.get(name_key="ballroom thieves")
        self.assertEqual((found.evidence, found.video_id), (Evidence.CHANNEL_SONG, "own00000001"))

    def test_same_name_different_band(self):
        upcoming_event("Epicenter")
        apple("epicenter", "100000077")
        self.apple = FakeAppleMusic(songs={"100000077": apple_music_fixture.top_songs("200000001", "300000001")})
        # the fake's top song is called "A Song"
        live = video("epi00000001", "UCEpicenterBand000000001", "Epicenter", "Epicenter - Live at the Fest")
        web = FakeWeb(searches={"Epicenter A Song": ["epi00000001"]}, videos={"epi00000001": live})
        self.run_command(web)
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="epicenter").status, Status.NOT_FOUND)

    def test_cover_or_fan_upload(self):
        self.ballroom()
        cover = video("cov00000001", "UCguitarjoe0000000000001", "guitarjoe", "The Ballroom Thieves - Archers (cover)")
        web = FakeWeb(searches={BALLROOM_QUERY: ["cov00000001"]}, videos={"cov00000001": cover})
        self.run_command(web)
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="ballroom thieves").status, Status.NOT_FOUND)

    def test_topic_video_of_another_album_doesnt_confirm(self):
        self.ballroom()
        other = video(
            BALLROOM_VIDEO, BALLROOM_TOPIC, "The Ballroom Thieves - Topic", "Archers",
            topic_description("Archers", "The Ballroom Thieves", "Some Other Record"),
        )
        web = FakeWeb(searches={BALLROOM_QUERY: [BALLROOM_VIDEO]}, videos={BALLROOM_VIDEO: other})
        self.run_command(web)
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="ballroom thieves").status, Status.NOT_FOUND)

    def test_not_embeddable(self):
        self.ballroom()
        web = FakeWeb(searches={BALLROOM_QUERY: [BALLROOM_VIDEO]}, videos={BALLROOM_VIDEO: topic_video(embeddable=False)})
        self.run_command(web)
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="ballroom thieves").status, Status.NOT_FOUND)

    def test_only_ids_stored(self):
        self.ballroom()
        web = FakeWeb(searches={BALLROOM_QUERY: [BALLROOM_VIDEO]}, videos={BALLROOM_VIDEO: topic_video()})
        self.run_command(web)
        stored = YouTubeArtistLink.objects.values().get()
        for value in stored.values():
            self.assertNotIn("Archers", str(value))
            self.assertNotIn("Wolf", str(value))


class QuotaTestCase(CommandTestCase):
    def several(self, count):
        searches = {}
        for i in range(count):
            name = f"Band Number {i:03d}"
            upcoming_event(name)
            apple(f"band number {i:03d}", str(500000 + i))
            searches[f"{name} A Song"] = []
        self.apple = FakeAppleMusic(
            songs={
                **BALLROOM_SONGS,
                **{str(500000 + i): apple_music_fixture.top_songs("200000001", "300000001") for i in range(count)},
            }
        )
        return searches

    def test_limit_reached(self):
        web = FakeWeb(searches=self.several(5))
        self.run_command(web, "--limit", "3")
        self.assertEqual(len(web.search_queries), 3)
        self.assertEqual(YouTubeArtistLink.objects.count(), 3)
        run = JobRun.objects.get(command="match_youtube_artists")
        self.assertEqual(dict(run.summary)["left for the next run"], 2)

    def test_quota_exhausted(self):
        self.ballroom()
        searches = self.several(2)
        searches["Band Number 001 A Song"] = quota_exceeded()
        searches[BALLROOM_QUERY] = [BALLROOM_VIDEO]
        web = FakeWeb(searches=searches, videos={BALLROOM_VIDEO: topic_video()})
        out = self.run_command(web)
        requests_after_quota = web.youtube_requests[[r.params.get("q") for r in web.youtube_requests].index("Band Number 001 A Song") + 1 :]
        self.assertEqual(requests_after_quota, [])
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="ballroom thieves").status, Status.MATCHED)
        self.assertIn("stopped early", out)
        self.assertIn("youtube-play", Event.objects.get(artists="The Ballroom Thieves").baked_html_template)


class RefreshTestCase(CommandTestCase):
    def test_refresh_keeps_a_live_video(self):
        self.ballroom()
        link("ballroom thieves", days_ago=31)
        web = FakeWeb(videos={BALLROOM_VIDEO: topic_video()})
        self.run_command(web)
        found = YouTubeArtistLink.objects.get(name_key="ballroom thieves")
        self.assertEqual((found.status, found.video_id), (Status.MATCHED, BALLROOM_VIDEO))
        self.assertGreater(found.checked_at, when(1))
        self.assertEqual(web.search_queries, [])

    def test_recent_link_not_checked(self):
        self.ballroom()
        link("ballroom thieves", days_ago=5)
        web = FakeWeb()
        self.run_command(web)
        self.assertEqual(web.requests, [])

    def test_video_removed(self):
        self.ballroom()
        link("ballroom thieves", days_ago=31, video_id="gone0000000")
        event = Event.objects.get(artists="The Ballroom Thieves")
        event.save()
        event.refresh_from_db()
        self.assertIn("gone0000000", event.baked_html_template)
        web = FakeWeb(searches={BALLROOM_QUERY: [BALLROOM_VIDEO]}, videos={BALLROOM_VIDEO: topic_video()})
        self.run_command(web)
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="ballroom thieves").video_id, BALLROOM_VIDEO)
        event.refresh_from_db()
        self.assertIn(BALLROOM_VIDEO, event.baked_html_template)
        self.assertNotIn("gone0000000", event.baked_html_template)

    def test_editors_video_removed(self):
        self.ballroom()
        link("ballroom thieves", days_ago=31, video_id="gone0000000", source=Source.EDITOR, evidence=Evidence.EDITOR)
        web = FakeWeb()
        self.run_command(web)
        found = YouTubeArtistLink.objects.get(name_key="ballroom thieves")
        self.assertEqual((found.status, found.source, found.video_id), (Status.NOT_FOUND, Source.EDITOR, "gone0000000"))
        self.assertEqual(web.search_queries, [])

    def test_editors_no_youtube_never_matched(self):
        self.ballroom()
        link("ballroom thieves", days_ago=60, status=Status.NONE, source=Source.EDITOR, evidence=Evidence.EDITOR, video_id="", channel_id="")
        web = FakeWeb()
        self.run_command(web)
        self.assertEqual(web.requests, [])

    def test_link_no_longer_needed(self):
        link("gone band", days_ago=31)
        self.run_command(FakeWeb())
        self.assertFalse(YouTubeArtistLink.objects.filter(name_key="gone band").exists())
