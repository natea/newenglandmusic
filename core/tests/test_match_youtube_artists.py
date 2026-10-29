import datetime
from io import StringIO
from unittest import mock

from core.music_ids import MUSICBRAINZ_TRIES
from core.models import AppleMusicArtistLink, Event, JobRun, SpotifyArtistLink, YouTubeArtistLink
from core.tests import apple_music_fixture
from core.tests import lastfm_fixture
from core.tests.lastfm_fixture import FakeLastFm
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
        # apple music is never asked: its terms rule its songs out for finding music elsewhere
        self.apple_requests = []
        self.enterContext(
            mock.patch("core.apple_music.AppleMusicClient.get", side_effect=lambda *a, **k: self.apple_requests.append(a))
        )
        # knows only the ballroom thieves' top track, unless a test adds more
        self.lastfm = FakeLastFm()
        self.lastfm.add_song("The Ballroom Thieves", "Archers", "A Wolf in the Doorway")

    def run_command(self, web, *args):
        out = StringIO()
        with (
            web.patch(),
            self.lastfm.patch("core.management.commands.match_youtube_artists.LastFm"),
            mock.patch.dict("os.environ", lastfm_fixture.CONFIGURED),
        ):
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
        self.assertEqual(len([r for r in web.requests if "musicbrainz" in r.url]), MUSICBRAINZ_TRIES)

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
        self.lastfm.add_song("Epicenter", "Glass Hours", "Glass Hours")
        live = video("epi00000001", "UCEpicenterBand000000001", "Epicenter", "Epicenter - Live at the Fest")
        web = FakeWeb(searches={"Epicenter Glass Hours": ["epi00000001"]}, videos={"epi00000001": live})
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
            self.lastfm.add_song(name, "A Song", "An Album")
            searches[f"{name} A Song"] = []
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


class LastFmSongTestCase(CommandTestCase):
    def spotify_only(self):
        upcoming_event("157frq")
        spotify("157frq", "157frqSpotifyArtist001")

    def own_video(self):
        return video("0Hr00AfSxNI", "UCSi9rQAM9Fuc7YCAsETd2gg", "157frq", "157frq - Spine (Official Music Video)")

    def test_spotify_only_artist_confirmed_with_its_lastfm_top_track(self):
        self.spotify_only()
        self.lastfm = FakeLastFm(
            pages={"157frq": lastfm_fixture.fixture("no_mbid.json")},
            tracks={"157frq": lastfm_fixture.fixture("top_tracks_157frq.json")},
            albums={("157frq", "Spine"): lastfm_fixture.fixture("track_spine.json")},
        )
        web = FakeWeb(searches={"157frq Spine": ["0Hr00AfSxNI"]}, videos={"0Hr00AfSxNI": self.own_video()})
        self.run_command(web)
        found = YouTubeArtistLink.objects.get(name_key="157frq")
        self.assertEqual((found.status, found.evidence, found.video_id), (Status.MATCHED, Evidence.CHANNEL_SONG, "0Hr00AfSxNI"))
        stored = " ".join(str(v) for v in YouTubeArtistLink.objects.values().get().values())
        self.assertNotIn("Spine", stored)

    def test_spotify_only_artist_whose_lastfm_page_is_shared(self):
        self.spotify_only()
        self.lastfm = FakeLastFm(
            pages={"157frq": lastfm_fixture.page("157frq", bio="There are at least two bands using the name 157frq.")},
            tracks={"157frq": lastfm_fixture.fixture("top_tracks_157frq.json")},
        )
        web = FakeWeb(searches={"157frq Spine": ["0Hr00AfSxNI"]}, videos={"0Hr00AfSxNI": self.own_video()})
        self.run_command(web)
        self.assertEqual(web.search_queries, [])
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="157frq").status, Status.NOT_FOUND)
        self.assertNotIn("artist.getTopTracks", self.lastfm.methods)

    def test_spotify_only_artist_with_no_top_tracks(self):
        self.spotify_only()
        self.lastfm = FakeLastFm(
            pages={"157frq": lastfm_fixture.fixture("no_mbid.json")},
            tracks={"157frq": lastfm_fixture.fixture("no_top_tracks.json")},
        )
        web = FakeWeb()
        self.run_command(web)
        self.assertEqual(web.search_queries, [])
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="157frq").status, Status.NOT_FOUND)

    def test_lastfm_rate_limit_leaves_song_names_for_the_next_run(self):
        self.spotify_only()
        self.ballroom()
        upcoming_event("Dinosaur Jr.")
        spotify("dinosaur jr", DINOSAUR_SPOTIFY)
        self.lastfm.pages["157frq"] = lastfm_fixture.fixture("rate_limited.json")
        web = FakeWeb(
            searches={BALLROOM_QUERY: [BALLROOM_VIDEO]}, videos={BALLROOM_VIDEO: topic_video()},
            wikidata={("P1902", DINOSAUR_SPOTIFY): [DINOSAUR_CHANNEL]}, channels={DINOSAUR_CHANNEL},
        )
        out = self.run_command(web)
        self.assertIn("carrying on without last.fm", out)
        # id-linked matches carry on; names needing a song are left, not marked not found
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="dinosaur jr").status, Status.MATCHED)
        self.assertFalse(YouTubeArtistLink.objects.filter(name_key__in=["157frq", "ballroom thieves"]).exists())
        self.assertEqual(web.search_queries, [])

    def test_apple_music_data_isnt_used(self):
        self.ballroom()
        web = FakeWeb(searches={BALLROOM_QUERY: [BALLROOM_VIDEO]}, videos={BALLROOM_VIDEO: topic_video()})
        self.run_command(web)
        self.assertEqual(self.apple_requests, [])
        self.assertIn("artist.getTopTracks", self.lastfm.methods)
        found = YouTubeArtistLink.objects.get(name_key="ballroom thieves")
        self.assertEqual((found.evidence, found.song_source), (Evidence.TOPIC_SONG, "lastfm"))

    def test_topic_video_with_no_album_from_lastfm(self):
        self.ballroom()
        self.lastfm.add_song("The Ballroom Thieves", "Archers")
        web = FakeWeb(searches={BALLROOM_QUERY: [BALLROOM_VIDEO]}, videos={BALLROOM_VIDEO: topic_video()})
        self.run_command(web)
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="ballroom thieves").status, Status.NOT_FOUND)

    def test_shared_lastfm_page_for_an_apple_matched_name(self):
        self.ballroom()
        self.lastfm.add_song("The Ballroom Thieves", "Archers", "A Wolf in the Doorway", bio="There are at least two bands using the name.")
        web = FakeWeb(searches={BALLROOM_QUERY: [BALLROOM_VIDEO]}, videos={BALLROOM_VIDEO: topic_video()})
        self.run_command(web)
        self.assertEqual(web.search_queries, [])
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="ballroom thieves").status, Status.NOT_FOUND)


class RematchTestCase(CommandTestCase):
    def test_old_match_confirmed_again(self):
        self.ballroom()
        link("ballroom thieves", days_ago=2, song_source="apple")
        web = FakeWeb(searches={BALLROOM_QUERY: [BALLROOM_VIDEO]}, videos={BALLROOM_VIDEO: topic_video()})
        self.run_command(web)
        found = YouTubeArtistLink.objects.get(name_key="ballroom thieves")
        self.assertEqual((found.status, found.video_id, found.song_source), (Status.MATCHED, BALLROOM_VIDEO, "lastfm"))
        self.assertGreater(found.checked_at, when(1))
        self.assertEqual(web.search_queries, [BALLROOM_QUERY])

    def test_old_match_not_confirmed(self):
        self.ballroom()
        link("ballroom thieves", days_ago=2, song_source="apple")
        event = Event.objects.get(artists="The Ballroom Thieves")
        event.save()
        event.refresh_from_db()
        self.assertIn("youtube-play", event.baked_html_template)
        self.lastfm = FakeLastFm()
        self.run_command(FakeWeb())
        self.assertEqual(YouTubeArtistLink.objects.get(name_key="ballroom thieves").status, Status.NOT_FOUND)
        event.refresh_from_db()
        self.assertNotIn("youtube-play", event.baked_html_template)

    def test_other_links_unaffected(self):
        self.ballroom()
        link("ballroom thieves", days_ago=2, source=Source.EDITOR, evidence=Evidence.EDITOR, song_source="apple")
        upcoming_event("Dinosaur Jr.")
        spotify("dinosaur jr", DINOSAUR_SPOTIFY)
        link("dinosaur jr", days_ago=2, evidence=Evidence.WIKIDATA, channel_id=DINOSAUR_CHANNEL, video_id="")
        web = FakeWeb()
        self.run_command(web)
        self.assertEqual(web.requests, [])

    def test_migration_marks_the_old_song_matches(self):
        from importlib import import_module

        from django.apps import apps

        link("old topic", evidence=Evidence.TOPIC_SONG)
        link("old channel", evidence=Evidence.CHANNEL_SONG)
        link("by wikidata", evidence=Evidence.WIKIDATA)
        link("by editor", evidence=Evidence.CHANNEL_SONG, source=Source.EDITOR)
        import_module("core.migrations.0090_youtube_link_song_source").mark_apple_song_matches(apps, None)
        self.assertEqual(
            dict(YouTubeArtistLink.objects.values_list("name_key", "song_source")),
            {"old topic": "apple", "old channel": "apple", "by wikidata": "", "by editor": ""},
        )
