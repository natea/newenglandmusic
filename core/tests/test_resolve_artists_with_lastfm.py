import datetime
from io import StringIO
from unittest import mock

from core.models import AppleMusicArtistLink, Event, JobRun, SpotifyArtistLink, Venue
from core.tests import apple_music_fixture
from core.tests.apple_music_fixture import FakeAppleMusic
from core.tests.lastfm_fixture import CONFIGURED, TEST_KEY, FakeLastFm, fixture, page
from core.tests.spotify_fixture import CREDENTIALS as SPOTIFY_CREDENTIALS
from core.tests.youtube_fixture import FakeWeb
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

Status, Source = SpotifyArtistLink.Status, SpotifyArtistLink.Source
COMMAND = "core.management.commands.resolve_artists_with_lastfm"
LUCAS_MBID = "7f1b5a39-3f4b-4f8e-9a4e-1f0c2d1d6a11"
BONOBO_MBID = "9a709693-b4f8-4da9-8cc1-038c911a61be"
DEAD_WEIGHT_MBID = "1d2c3b4a-0000-4000-8000-00000000dead"
DEUCES_MBID = "2e3d4c5b-0000-4000-8000-00000000dec5"
LUCAS_SPOTIFY = "4DjLucasSpotifyArtist01"[:22]
BONOBO_SPOTIFY = "0cmWgDlu9CwTgxPhf403hb"


def spotify_url(artist_id):
    return f"https://open.spotify.com/artist/{artist_id}"


def when(days_ago=0):
    return timezone.now() - datetime.timedelta(days=days_ago)


def ambiguous(name_key, model=SpotifyArtistLink, **fields):
    return model.objects.create(
        name_key=name_key, status=model.Status.AMBIGUOUS, checked_at=when(), last_seen_at=when(), **fields
    )


class ResolveTestCase(TestCase):
    def setUp(self):
        env = {**CONFIGURED, **SPOTIFY_CREDENTIALS, **apple_music_fixture.SWITCHED_ON}
        self.enterContext(mock.patch.dict("os.environ", env))
        Venue.objects.create(name="Sally O'Brien's", state="MA", city_town="Somerville")
        self.lastfm = FakeLastFm(pages={
            "DJ Lucas": fixture("dj_lucas.json"), "Bonobo": fixture("bonobo.json"),
            "Dead Weight": fixture("dead_weight.json"), "Deuces Wild": fixture("deuces_wild.json"),
            "157frq": fixture("no_mbid.json"),
        })
        self.web = FakeWeb(mb_artists={
            LUCAS_MBID: {"name": "DJ Lucas", "area": "Massachusetts", "urls": [spotify_url(LUCAS_SPOTIFY)]},
            BONOBO_MBID: {"name": "Bonobo", "area": "United Kingdom", "begin_area": "Brighton",
                          "urls": [spotify_url(BONOBO_SPOTIFY), "https://music.apple.com/us/artist/bonobo/489634654"]},
            DEAD_WEIGHT_MBID: {"name": "Dead Weight", "begin_area": "St Albans", "urls": [spotify_url("1DeadWeightSpotify0001")]},
            DEUCES_MBID: {"name": "Deuces Wild", "area": "Germany", "urls": [spotify_url("1DeucesWildSpotify0001")]},
        })
        self.apple = FakeAppleMusic(songs={"489634654": apple_music_fixture.fixture("top_songs.json")})

    def event(self, artists):
        return Event.objects.create(artists=artists, starttime=timezone.now() + datetime.timedelta(days=3))

    def run_command(self, *args):
        out = StringIO()
        with (
            self.lastfm.patch(f"{COMMAND}.LastFm"),
            mock.patch(f"{COMMAND}.MusicIds", lambda: self.web.music_ids()),
            self.apple.patch(f"{COMMAND}.AppleMusicClient"),
        ):
            call_command("resolve_artists_with_lastfm", *args, stdout=out)
        return out.getvalue()

    def link(self, name_key, model=SpotifyArtistLink):
        return model.objects.get(name_key=name_key)

    def test_local_act(self):
        self.event("DJ Lucas")
        ambiguous("dj lucas")
        self.run_command()
        found = self.link("dj lucas")
        self.assertEqual((found.status, found.spotify_artist_id, found.source), (Status.MATCHED, LUCAS_SPOTIFY, Source.EVIDENCE))

    def test_dominant_touring_act(self):
        event = self.event("Bonobo")
        ambiguous("bonobo")
        out = self.run_command()
        found = self.link("bonobo")
        self.assertEqual((found.status, found.spotify_artist_id, found.source), (Status.MATCHED, BONOBO_SPOTIFY, Source.EVIDENCE))
        self.assertIn("dominant", out)
        event.refresh_from_db()
        self.assertIn(f'data-spotify-artist="{BONOBO_SPOTIFY}"', event.baked_html_template)

    def test_shared_name_flagged_on_lastfm(self):
        self.event("Dead Weight")
        ambiguous("dead weight")
        self.run_command()
        found = self.link("dead weight")
        self.assertEqual((found.status, found.source, found.spotify_artist_id), (Status.AMBIGUOUS, Source.AUTO, ""))
        self.assertIsNotNone(found.evidence_checked_at)

    def test_small_act_from_elsewhere(self):
        self.event("Deuces Wild")
        ambiguous("deuces wild")
        self.run_command()
        self.assertEqual(self.link("deuces wild").status, Status.AMBIGUOUS)

    def test_no_musicbrainz_id_or_link(self):
        self.event("157frq, Nobody Here")
        ambiguous("157frq")
        ambiguous("nobody here")
        self.web.mb_artists[LUCAS_MBID]["urls"] = []
        self.event("DJ Lucas")
        ambiguous("dj lucas")
        self.run_command()
        for key in ("157frq", "nobody here", "dj lucas"):
            self.assertEqual(self.link(key).status, Status.AMBIGUOUS)

    def test_different_name_on_musicbrainz(self):
        self.event("Bonobo")
        ambiguous("bonobo")
        self.web.mb_artists[BONOBO_MBID]["name"] = "Bonobo Orchestra"
        self.run_command()
        self.assertEqual(self.link("bonobo").status, Status.AMBIGUOUS)

    def test_apple_music_link_resolved(self):
        event = self.event("Bonobo")
        ambiguous("bonobo", model=AppleMusicArtistLink)
        self.run_command()
        found = self.link("bonobo", AppleMusicArtistLink)
        self.assertEqual(
            (found.status, found.apple_artist_id, found.top_song_id, found.source),
            (Status.MATCHED, "489634654", "964625539", Source.EVIDENCE),
        )
        event.refresh_from_db()
        self.assertIn('data-apple-artist="489634654"', event.baked_html_template)

    def test_recently_considered(self):
        self.event("Bonobo")
        ambiguous("bonobo", evidence_checked_at=when(10))
        self.run_command()
        self.assertEqual(self.lastfm.requests, [])
        self.assertEqual(self.link("bonobo").status, Status.AMBIGUOUS)

    def test_evidence_gone(self):
        event = self.event("Bonobo")
        SpotifyArtistLink.objects.create(
            name_key="bonobo", status=Status.MATCHED, spotify_artist_id=BONOBO_SPOTIFY, source=Source.EVIDENCE,
            checked_at=when(31), last_seen_at=when(), evidence_checked_at=when(31),
        )
        event.save()
        self.web.mb_artists[BONOBO_MBID]["urls"] = []
        self.run_command()
        found = self.link("bonobo")
        self.assertEqual((found.status, found.source, found.spotify_artist_id), (Status.AMBIGUOUS, Source.AUTO, ""))
        event.refresh_from_db()
        self.assertNotIn("spotify-play", event.baked_html_template)

    def test_evidence_still_holds(self):
        self.event("Bonobo")
        SpotifyArtistLink.objects.create(
            name_key="bonobo", status=Status.MATCHED, spotify_artist_id=BONOBO_SPOTIFY, source=Source.EVIDENCE,
            checked_at=when(31), last_seen_at=when(), evidence_checked_at=when(31),
        )
        self.run_command()
        found = self.link("bonobo")
        self.assertEqual((found.status, found.source), (Status.MATCHED, Source.EVIDENCE))
        self.assertGreater(found.evidence_checked_at, when(1))

    def test_revert(self):
        events = [self.event(name) for name in ("Bonobo", "DJ Lucas", "Dead Weight")]
        for key, artist_id in (("bonobo", BONOBO_SPOTIFY), ("dj lucas", LUCAS_SPOTIFY), ("dead weight", "1DeadWeightSpotify0001")):
            SpotifyArtistLink.objects.create(
                name_key=key, status=Status.MATCHED, spotify_artist_id=artist_id, source=Source.EVIDENCE,
                checked_at=when(), last_seen_at=when(), evidence_checked_at=when(),
            )
        for event in events:
            event.save()
        self.run_command("--revert")
        self.assertEqual(set(SpotifyArtistLink.objects.values_list("status", "source")), {(Status.AMBIGUOUS, Source.AUTO)})
        for event in events:
            event.refresh_from_db()
            self.assertNotIn("spotify-play", event.baked_html_template)

    def test_nothing_kept(self):
        self.event("DJ Lucas")
        ambiguous("dj lucas")
        self.run_command()
        stored = " ".join(str(value) for value in SpotifyArtistLink.objects.values().get().values())
        for kept in ("Massachusetts", "20133", LUCAS_MBID, "rapper"):
            self.assertNotIn(kept, stored)

    def test_rate_limited(self):
        self.event("Bonobo, Dead Weight, Deuces Wild")
        for key in ("bonobo", "dead weight", "deuces wild"):
            ambiguous(key)
        self.lastfm.pages["Dead Weight"] = fixture("rate_limited.json")
        out = self.run_command()
        self.assertEqual(self.link("bonobo").status, Status.MATCHED)
        self.assertEqual(self.lastfm.methods, ["artist.getInfo", "artist.getInfo"])
        self.assertIsNone(self.link("deuces wild").evidence_checked_at)
        self.assertIn("stopped early, 2 names left", out)
        run = JobRun.objects.get(command="resolve_artists_with_lastfm")
        self.assertEqual(dict(run.summary)["left for the next run"], 2)

    def test_musicbrainz_busy_leaves_names(self):
        self.event("Bonobo")
        ambiguous("bonobo")
        self.web.musicbrainz_503s = 10
        out = self.run_command()
        self.assertIn("stopping this run", out)
        self.assertIsNone(self.link("bonobo").evidence_checked_at)

    def test_key_out_of_errors(self):
        self.event("Bonobo")
        ambiguous("bonobo")
        self.lastfm.pages["Bonobo"] = {"error": 10, "message": "Invalid API key - You must be granted a valid key by last.fm"}
        out = self.run_command()
        self.assertNotIn(TEST_KEY, out)
        self.assertNotIn("audioscrobbler", out)
        self.assertIn("failed", out)

    def test_not_configured(self):
        self.event("Bonobo")
        ambiguous("bonobo")
        with mock.patch.dict("os.environ", {"LASTFM_API_KEY": ""}):
            out = self.run_command()
        self.assertIn("isn't configured", out)
        self.assertEqual(self.lastfm.requests, [])
        self.assertEqual(self.link("bonobo").status, Status.AMBIGUOUS)

    def test_dry_run(self):
        self.event("Bonobo")
        ambiguous("bonobo")
        out = self.run_command("--dry-run")
        self.assertIn(f"Bonobo: Spotify {BONOBO_SPOTIFY} (dominant", out)
        found = self.link("bonobo")
        self.assertEqual((found.status, found.evidence_checked_at), (Status.AMBIGUOUS, None))

    def test_editor_links_left_alone(self):
        self.event("Bonobo")
        SpotifyArtistLink.objects.create(
            name_key="bonobo", status=Status.AMBIGUOUS, source=Source.EDITOR, checked_at=when(), last_seen_at=when()
        )
        self.run_command()
        self.assertEqual(self.lastfm.requests, [])


class LocalRuleTestCase(ResolveTestCase):
    def test_shared_page_bio_place_doesnt_count(self):
        # "Alien": a numbered bio of several acts, one mentioning someone named Somerville
        self.event("Alien")
        ambiguous("alien")
        mbid = "3a4b5c6d-0000-4000-8000-0000000a11e7"
        self.lastfm.pages["Alien"] = page("Alien", mbid, 30000, "1) - Alien is a Swedish band formed in Gothenburg. 2) Alien is a rapper from Western Massachusetts.")
        self.web.mb_artists[mbid] = {"name": "Alien", "area": "Sweden", "begin_area": "Gothenburg", "urls": [spotify_url("1AlienSwedenSpotify001")]}
        self.run_command()
        self.assertEqual(self.link("alien").status, Status.AMBIGUOUS)

    def test_same_named_town_in_another_country(self):
        # The Blue Stones: begin area Windsor, Ontario, while the site has a venue in Windsor, CT
        Venue.objects.create(name="Windsor hall", state="CT", city_town="Windsor")
        self.event("The Blue Stones")
        ambiguous("blue stones")
        mbid = "5c6d7e8f-0000-4000-8000-0000000b1e55"
        self.lastfm.pages["The Blue Stones"] = page("The Blue Stones", mbid, 60000, "")
        self.web.mb_artists[mbid] = {"name": "The Blue Stones", "begin_area": "Windsor", "urls": [spotify_url("1BlueStonesSpotify0001")]}
        self.run_command()
        self.assertEqual(self.link("blue stones").status, Status.AMBIGUOUS)

    def test_covered_town_as_musicbrainz_area(self):
        self.event("Small Town Band")
        ambiguous("small town band")
        mbid = "4b5c6d7e-0000-4000-8000-00000000b0b5"
        self.lastfm.pages["Small Town Band"] = page("Small Town Band", mbid, 900, "")
        self.web.mb_artists[mbid] = {"name": "Small Town Band", "area": "Somerville", "urls": [spotify_url("1SmallTownBandSpot0001")]}
        self.run_command()
        self.assertEqual(self.link("small town band").status, Status.MATCHED)


class ReasonsTestCase(ResolveTestCase):
    def test_every_line_says_why(self):
        self.event("Bonobo, Dead Weight, Deuces Wild, 157frq, Nobody Here")
        for key in ("bonobo", "dead weight", "deuces wild", "157frq", "nobody here"):
            ambiguous(key)
        ambiguous("bonobo", model=AppleMusicArtistLink)
        self.web.mb_artists[BONOBO_MBID]["urls"] = [spotify_url(BONOBO_SPOTIFY)]
        out = self.run_command("--dry-run")
        self.assertIn("Bonobo: Spotify 0cmWgDlu9CwTgxPhf403hb (dominant: 2,121,800 Last.fm listeners)", out)
        self.assertIn("Bonobo: Apple Music stays ambiguous (MusicBrainz links no Apple Music artists)", out)
        self.assertIn("Dead Weight: Spotify stays ambiguous (Last.fm says several acts share the name)", out)
        self.assertIn("Deuces Wild: Spotify stays ambiguous (neither local nor dominant: 2,032 Last.fm listeners, MusicBrainz area Germany)", out)
        self.assertIn("157frq: Spotify stays ambiguous (the Last.fm page has no MusicBrainz ID)", out)
        self.assertIn("Nobody Here: Spotify stays ambiguous (no Last.fm page)", out)

    def test_different_name_reason(self):
        self.event("Bonobo")
        ambiguous("bonobo")
        self.web.mb_artists[BONOBO_MBID]["name"] = "Bonobo Orchestra"
        self.assertIn('stays ambiguous (MusicBrainz calls the Last.fm page\'s act "Bonobo Orchestra")', self.run_command("--dry-run"))

    def test_local_reason_names_the_state(self):
        self.event("DJ Lucas")
        ambiguous("dj lucas")
        self.assertIn("(local: MusicBrainz area Massachusetts (US-MA))", self.run_command("--dry-run"))
