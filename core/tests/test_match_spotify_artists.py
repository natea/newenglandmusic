import datetime
from io import StringIO
from unittest import mock

from core.models import Event, JobRun, SpotifyArtistLink
from core.spotify import SpotifyBlocked, SpotifyBusy, SpotifyError, parse_artist_id
from core.tests.spotify_fixture import CREDENTIALS, FakeSpotify, fixture, rate_limited, response
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

Status = SpotifyArtistLink.Status


def upcoming_event(title=None, artists=None, days=3, **fields):
    return Event.objects.create(
        title=title, artists=artists, starttime=timezone.now() + datetime.timedelta(days=days), **fields
    )


def link(name_key, days_ago=0, **fields):
    when = timezone.now() - datetime.timedelta(days=days_ago)
    defaults = {"status": Status.MATCHED, "spotify_artist_id": "fakeOld", "checked_at": when, "last_seen_at": when}
    return SpotifyArtistLink.objects.create(name_key=name_key, **{**defaults, **fields})


@mock.patch.dict("os.environ", CREDENTIALS)
class MatchingTestCase(TestCase):
    def run_command(self, spotify, *args):
        out = StringIO()
        with spotify.patch():
            call_command("match_spotify_artists", *args, stdout=out)
        return out.getvalue()

    def test_unique_exact_match(self):
        upcoming_event(artists="The Ballroom Thieves")
        spotify = FakeSpotify({"The Ballroom Thieves": fixture("search_unique.json")})
        self.run_command(spotify)
        found = SpotifyArtistLink.objects.get(name_key="ballroom thieves")
        self.assertEqual((found.status, found.spotify_artist_id), (Status.MATCHED, "fakeBallroomThieves01"))
        self.assertEqual(found.source, SpotifyArtistLink.Source.AUTO)
        self.assertEqual(spotify.searches[0].params, {"q": "The Ballroom Thieves", "type": "artist", "limit": 10})

    def test_two_artists_with_the_same_name(self):
        upcoming_event(artists="Epicenter")
        self.run_command(FakeSpotify({"Epicenter": fixture("search_same_name.json")}))
        found = SpotifyArtistLink.objects.get(name_key="epicenter")
        self.assertEqual((found.status, found.spotify_artist_id), (Status.AMBIGUOUS, ""))

    def test_no_exact_match(self):
        upcoming_event(artists="Haven's Den")
        self.run_command(FakeSpotify({"Haven's Den": fixture("search_no_exact.json")}))
        self.assertEqual(SpotifyArtistLink.objects.get(name_key="havens den").status, Status.NOT_FOUND)

    def test_same_name_on_many_events_searched_once(self):
        for days in range(1, 5):
            upcoming_event(artists="Lake Street Dive", days=days)
        spotify = FakeSpotify()
        self.run_command(spotify)
        self.assertEqual([s.params["q"] for s in spotify.searches], ["Lake Street Dive"])

    def test_dry_run_saves_nothing(self):
        upcoming_event(artists="The Ballroom Thieves")
        out = self.run_command(FakeSpotify({"The Ballroom Thieves": fixture("search_unique.json")}), "--dry-run")
        self.assertIn("The Ballroom Thieves: matched -> fakeBallroomThieves01", out)
        self.assertFalse(SpotifyArtistLink.objects.exists())

    def test_names_and_limit(self):
        upcoming_event(artists="Arto Vaun, Shadow Monster, Dyr Faser")
        spotify = FakeSpotify()
        self.run_command(spotify, "--names", "Shadow Monster,Dyr Faser", "--limit", "1")
        self.assertEqual([s.params["q"] for s in spotify.searches], ["Dyr Faser"])

    def test_past_unapproved_and_non_music_events_ignored(self):
        upcoming_event(artists="Past Band", days=-2)
        upcoming_event(artists="Waiting Band", is_approved=False)
        upcoming_event(artists="Comedy Troupe", kind=Event.Kind.COMEDY)
        spotify = FakeSpotify()
        self.run_command(spotify)
        self.assertEqual(spotify.searches, [])

    def test_editor_links_never_searched(self):
        upcoming_event(artists="Epicenter")
        link("epicenter", days_ago=60, source=SpotifyArtistLink.Source.EDITOR, spotify_artist_id="fakeMine")
        spotify = FakeSpotify()
        self.run_command(spotify)
        self.assertEqual(spotify.searches, [])
        self.assertEqual(SpotifyArtistLink.objects.get().spotify_artist_id, "fakeMine")


@mock.patch.dict("os.environ", CREDENTIALS)
class StorageTestCase(TestCase):
    def run_command(self, spotify):
        with spotify.patch():
            call_command("match_spotify_artists", stdout=StringIO())

    def test_stale_automatic_match_rechecked(self):
        upcoming_event(artists="The Ballroom Thieves")
        old = link("ballroom thieves", days_ago=31)
        spotify = FakeSpotify({"The Ballroom Thieves": fixture("search_unique.json")})
        self.run_command(spotify)
        old.refresh_from_db()
        self.assertEqual(len(spotify.searches), 1)
        self.assertEqual(old.spotify_artist_id, "fakeBallroomThieves01")
        self.assertGreater(old.checked_at, timezone.now() - datetime.timedelta(minutes=1))

    def test_recent_match_not_rechecked(self):
        upcoming_event(artists="The Ballroom Thieves")
        link("ballroom thieves", days_ago=29)
        spotify = FakeSpotify()
        self.run_command(spotify)
        self.assertEqual(spotify.searches, [])

    def test_link_no_longer_needed_deleted(self):
        link("gone band", days_ago=31)
        link("gone by editor", days_ago=31, source=SpotifyArtistLink.Source.EDITOR)
        link("recent band", days_ago=10)
        self.run_command(FakeSpotify())
        self.assertEqual(list(SpotifyArtistLink.objects.values_list("name_key", flat=True)), ["recent band"])

    def test_seen_names_kept_fresh(self):
        upcoming_event(artists="Recent Band")
        old = link("recent band", days_ago=29, last_seen_at=timezone.now() - datetime.timedelta(days=40))
        self.run_command(FakeSpotify())
        old.refresh_from_db()
        self.assertGreater(old.last_seen_at, timezone.now() - datetime.timedelta(minutes=1))

    def test_nothing_else_stored(self):
        upcoming_event(artists="The Ballroom Thieves")
        self.run_command(FakeSpotify({"The Ballroom Thieves": fixture("search_unique.json")}))
        row = SpotifyArtistLink.objects.values().get()
        self.assertEqual(
            set(row), {"id", "name_key", "status", "spotify_artist_id", "source", "checked_at", "last_seen_at"}
        )
        # spotify's spelling, genres and urls aren't kept anywhere in the row
        self.assertNotIn("indie folk", str(row))
        self.assertNotIn("The Ballroom Thieves", str(row))

    def test_changed_links_rebake_their_events(self):
        event = upcoming_event(artists="The Ballroom Thieves")
        self.assertNotIn("spotify-play", Event.objects.get(pk=event.pk).baked_html_template)
        self.run_command(FakeSpotify({"The Ballroom Thieves": fixture("search_unique.json")}))
        self.assertIn(
            'data-spotify-artist="fakeBallroomThieves01"', Event.objects.get(pk=event.pk).baked_html_template
        )


@mock.patch.dict("os.environ", CREDENTIALS)
class ThrottlingTestCase(TestCase):
    def test_rate_limited_then_succeeds(self):
        upcoming_event(artists="The Ballroom Thieves")
        spotify = FakeSpotify(
            {"The Ballroom Thieves": [rate_limited(3), response(200, fixture("search_unique.json"))]}
        )
        with spotify.patch():
            call_command("match_spotify_artists", stdout=StringIO())
        self.assertIn(3.0, spotify.sleeps)
        self.assertEqual(SpotifyArtistLink.objects.get().status, Status.MATCHED)

    def test_persistent_failure_leaves_link_and_continues(self):
        upcoming_event(artists="Epicenter, The Ballroom Thieves")
        old = link("epicenter", days_ago=31, spotify_artist_id="fakeOld")
        spotify = FakeSpotify(
            {
                "Epicenter": [rate_limited(), rate_limited(), rate_limited()],
                "The Ballroom Thieves": fixture("search_unique.json"),
            }
        )
        out = StringIO()
        with spotify.patch():
            call_command("match_spotify_artists", stdout=out)
        old.refresh_from_db()
        self.assertEqual((old.spotify_artist_id, old.checked_at < timezone.now() - datetime.timedelta(days=30)), ("fakeOld", True))
        self.assertTrue(SpotifyArtistLink.objects.filter(name_key="ballroom thieves").exists())
        self.assertIn("Epicenter: failed", out.getvalue())
        # backed off between the tries, as spotify gave no Retry-After
        self.assertIn(1, spotify.sleeps)
        self.assertIn(2, spotify.sleeps)

    def test_long_block_stops_the_run_and_keeps_what_it_found(self):
        event = upcoming_event(artists="Arto Vaun, The Ballroom Thieves, Shadow Monster")
        spotify = FakeSpotify(
            {
                "Arto Vaun": {"artists": {"items": [{"id": "fakeArto", "name": "Arto Vaun"}]}},
                # sorted names: arto vaun, ballroom thieves, shadow monster
                "The Ballroom Thieves": [rate_limited(85212)],
            }
        )
        out = StringIO()
        with spotify.patch():
            call_command("match_spotify_artists", stdout=out)
        # no waiting out a day-long block, and nothing more asked of spotify
        self.assertNotIn(85212.0, spotify.sleeps)
        self.assertEqual([s.params["q"] for s in spotify.searches], ["Arto Vaun", "The Ballroom Thieves"])
        self.assertEqual(list(SpotifyArtistLink.objects.values_list("name_key", flat=True)), ["arto vaun"])
        self.assertIn('data-spotify-artist="fakeArto"', Event.objects.get(pk=event.pk).baked_html_template)
        self.assertIn("stopped early, 1 names left", out.getvalue())
        summary = dict(JobRun.objects.get(command="match_spotify_artists").summary)
        self.assertEqual((summary["searched"], summary["failed"], summary["left for the next run"]), (2, 1, 1))

    def test_next_run_carries_on(self):
        upcoming_event(artists="Arto Vaun, Shadow Monster")
        link("arto vaun")
        spotify = FakeSpotify()
        with spotify.patch():
            call_command("match_spotify_artists", stdout=StringIO())
        self.assertEqual([s.params["q"] for s in spotify.searches], ["Shadow Monster"])

    def test_requests_spaced_apart(self):
        upcoming_event(artists="Arto Vaun, Shadow Monster")
        spotify = FakeSpotify()
        with spotify.patch():
            call_command("match_spotify_artists", stdout=StringIO())
        self.assertEqual(len(spotify.searches), 2)
        self.assertIn(0.5, spotify.sleeps)

    def test_job_summary(self):
        upcoming_event(
            artists="Ballroom Thieves, Epicenter, Havens Den, Nobody Here, Fails Always, "
            "Match Two, Match Three, Match Four, Match Five, Match Six"
        )
        for key in ("old one", "old two", "old three"):
            link(key, days_ago=40)
        results = {
            "Ballroom Thieves": fixture("search_unique.json"),
            "Epicenter": fixture("search_same_name.json"),
            "Havens Den": fixture("search_no_exact.json"),
            "Fails Always": [rate_limited(), rate_limited(), rate_limited()],
        }
        for n in ("Two", "Three", "Four", "Five", "Six"):
            results[f"Match {n}"] = {"artists": {"items": [{"id": f"fake{n}", "name": f"Match {n}"}]}}
        spotify = FakeSpotify(results)
        with spotify.patch():
            call_command("match_spotify_artists", stdout=StringIO())
        self.assertEqual(
            JobRun.objects.get(command="match_spotify_artists").summary,
            [
                ["searched", 10], ["matched", 6], ["ambiguous", 1], ["not found", 2], ["deleted", 3],
                ["failed", 1], ["left for the next run", 0],
            ],
        )


def found(*artists):
    return {"artists": {"items": [{"id": artist_id, "name": name} for name, artist_id in artists]}}


@mock.patch.dict("os.environ", CREDENTIALS)
class DuoAndOccasionTestCase(TestCase):
    def run_command(self, spotify, *args):
        out = StringIO()
        with spotify.patch():
            call_command("match_spotify_artists", *args, stdout=out)
        return out.getvalue()

    def searched(self, spotify):
        return [s.params["q"] for s in spotify.searches]

    def test_duo_acts_searched_when_the_duo_isnt_an_artist(self):
        event = upcoming_event(title="Chris Collins & Boulder Canyon")
        spotify = FakeSpotify({"Boulder Canyon": found(("Boulder Canyon", "fakeBoulder"))})
        self.run_command(spotify)
        self.assertEqual(
            self.searched(spotify), ["Chris Collins & Boulder Canyon", "Chris Collins", "Boulder Canyon"]
        )
        self.assertEqual(SpotifyArtistLink.objects.get(name_key="boulder canyon").spotify_artist_id, "fakeBoulder")
        self.assertIn('data-spotify-artist="fakeBoulder"', Event.objects.get(pk=event.pk).baked_html_template)

    def test_backing_band_not_searched(self):
        upcoming_event(artists="Chris Cote and his Band of These Guys")
        spotify = FakeSpotify()
        self.run_command(spotify)
        self.assertEqual(self.searched(spotify), ["Chris Cote and his Band of These Guys", "Chris Cote"])

    def test_duo_that_is_an_artist_not_split(self):
        upcoming_event(artists="AJ Lee & Blue Summit")
        spotify = FakeSpotify({"AJ Lee & Blue Summit": found(("AJ Lee & Blue Summit", "fakeAJ"))})
        self.run_command(spotify)
        self.assertEqual(self.searched(spotify), ["AJ Lee & Blue Summit"])

    def test_acts_of_a_duo_found_missing_before(self):
        upcoming_event(artists="Connor Garvey & Ben Cosgrove")
        link("connor garvey and ben cosgrove", status=SpotifyArtistLink.Status.NOT_FOUND, spotify_artist_id="")
        spotify = FakeSpotify()
        self.run_command(spotify)
        self.assertEqual(self.searched(spotify), ["Connor Garvey", "Ben Cosgrove"])

    def test_occasion_of_a_known_artist_needs_no_search(self):
        event = upcoming_event(title="Built to Spill Fall 2026 Tour")
        link("built to spill", spotify_artist_id="fakeBTS")
        spotify = FakeSpotify()
        self.run_command(spotify)
        self.assertEqual(spotify.searches, [])
        Event.objects.get(pk=event.pk).save()
        self.assertIn("▶ Built to Spill", Event.objects.get(pk=event.pk).baked_html_template)

    def test_occasion_found_among_its_search_results(self):
        event = upcoming_event(title="Corey Kent Heartland Rock and Roll Tour")
        spotify = FakeSpotify(
            {"Corey Kent Heartland Rock and Roll Tour": found(("Corey Kent", "fakeCK"), ("Heartland", "fakeH"))}
        )
        out = self.run_command(spotify)
        self.assertIn("an occasion of corey kent: matched -> fakeCK", out)
        self.assertEqual(SpotifyArtistLink.objects.get(name_key="corey kent").spotify_artist_id, "fakeCK")
        self.assertEqual(
            SpotifyArtistLink.objects.get(name_key="corey kent heartland rock and roll tour").status,
            SpotifyArtistLink.Status.NOT_FOUND,
        )
        html = Event.objects.get(pk=event.pk).baked_html_template
        self.assertIn('data-spotify-artist="fakeCK"', html)
        self.assertIn("▶ Corey Kent", html)

    def test_occasion_doesnt_overwrite_an_editors_choice(self):
        upcoming_event(title="Corey Kent Heartland Rock and Roll Tour")
        link("corey kent", source=SpotifyArtistLink.Source.EDITOR, spotify_artist_id="fakeMine")
        # corey kent is matched, so the occasion needs no search at all
        spotify = FakeSpotify()
        self.run_command(spotify)
        self.assertEqual(spotify.searches, [])
        self.assertEqual(SpotifyArtistLink.objects.get(name_key="corey kent").spotify_artist_id, "fakeMine")

    def test_limit_counts_the_acts_too(self):
        upcoming_event(title="Chris Collins & Boulder Canyon")
        spotify = FakeSpotify()
        self.run_command(spotify, "--limit", "2")
        self.assertEqual(self.searched(spotify), ["Chris Collins & Boulder Canyon", "Chris Collins"])

    def test_acts_and_artists_of_occasions_kept_fresh(self):
        upcoming_event(title="Built to Spill Fall 2026 Tour, Chris Collins & Boulder Canyon")
        for key in ("built to spill", "boulder canyon"):
            link(key, days_ago=10, last_seen_at=timezone.now() - datetime.timedelta(days=40))
        link("chris collins and boulder canyon", status=SpotifyArtistLink.Status.NOT_FOUND, spotify_artist_id="")
        self.run_command(FakeSpotify())
        self.assertEqual(
            set(SpotifyArtistLink.objects.values_list("name_key", flat=True)),
            {"built to spill", "boulder canyon", "chris collins and boulder canyon", "chris collins"},
        )


class NotConfiguredTestCase(TestCase):
    def test_does_nothing_without_credentials(self):
        upcoming_event(artists="The Ballroom Thieves")
        spotify = FakeSpotify()
        out = StringIO()
        with spotify.patch():
            call_command("match_spotify_artists", stdout=out)  # exits normally
        self.assertIn("spotify isn't configured", out.getvalue())
        self.assertEqual((spotify.searches, spotify.token_requests), ([], []))
        self.assertFalse(SpotifyArtistLink.objects.exists())


class ClientTestCase(SimpleTestCase):
    def test_token_uses_basic_auth_not_the_url(self):
        spotify = FakeSpotify()
        spotify.client().search_artists("Epicenter")
        self.assertEqual(spotify.token_requests[0].auth, ("fake-client-id", "fake-client-secret"))
        self.assertEqual(spotify.token_requests[0].data, {"grant_type": "client_credentials"})
        self.assertNotIn("fake-client-secret", spotify.searches[0].url + str(spotify.searches[0].params))
        self.assertEqual(spotify.searches[0].headers, {"Authorization": "Bearer fake-access-token"})

    def test_token_reused(self):
        spotify = FakeSpotify()
        client = spotify.client()
        client.search_artists("One")
        client.search_artists("Two")
        self.assertEqual(len(spotify.token_requests), 1)

    def test_401_gets_a_new_token_once(self):
        spotify = FakeSpotify({"One": [response(401, {"error": {"status": 401, "message": "expired"}}),
                                       response(200, fixture("search_unique.json"))]})
        self.assertEqual(len(spotify.client().search_artists("One")), 3)
        self.assertEqual(len(spotify.token_requests), 2)

    def test_error_message_is_spotifys_without_secrets(self):
        spotify = FakeSpotify({"One": [response(403, {"error": {"status": 403, "message": "Premium required"}})]})
        with self.assertRaises(SpotifyError) as raised:
            spotify.client().search_artists("One")
        self.assertIn("Premium required", str(raised.exception))
        for secret in ("fake-client-secret", "fake-access-token"):
            self.assertNotIn(secret, str(raised.exception))

    def test_long_retry_after_raises_blocked_without_waiting(self):
        spotify = FakeSpotify({"One": [rate_limited(85212)]})
        with self.assertRaises(SpotifyBlocked):
            spotify.client().search_artists("One")
        self.assertEqual(spotify.sleeps, [])

    def test_three_429s_raise_busy(self):
        spotify = FakeSpotify({"One": [rate_limited(), rate_limited(), rate_limited()]})
        with self.assertRaises(SpotifyBusy):
            spotify.client().search_artists("One")
        self.assertEqual(len(spotify.searches), 3)

    def test_parse_artist_id(self):
        self.assertEqual(parse_artist_id("https://open.spotify.com/artist/abc123?si=x"), "abc123")
        self.assertEqual(parse_artist_id("https://open.spotify.com/intl-de/artist/abc123"), "abc123")
        self.assertEqual(parse_artist_id("spotify:artist:abc123"), "abc123")
        self.assertIsNone(parse_artist_id("https://example.com/band"))
        self.assertIsNone(parse_artist_id("https://open.spotify.com/album/abc123"))
