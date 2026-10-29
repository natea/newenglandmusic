from core.artist_evidence import covered_places, is_covered_subdivision, is_dominant, names_covered_place, shares_name
from core.lastfm import MIN_SECONDS_BETWEEN_REQUESTS, LastFmError, LastFmStopped
from core.models import Venue
from core.tests.lastfm_fixture import TEST_KEY, FakeLastFm, fixture, response
from core.tests.youtube_fixture import FakeWeb, area_id
from django.test import SimpleTestCase, TestCase


class LastFmClientTestCase(SimpleTestCase):
    def test_artist_info(self):
        lastfm = FakeLastFm(pages={"Bonobo": fixture("bonobo.json")})
        info = lastfm.client().artist_info("Bonobo")
        self.assertEqual(info["mbid"], "9a709693-b4f8-4da9-8cc1-038c911a61be")
        self.assertEqual(info["listeners"], 2121800)
        self.assertIn("British musician", info["bio"])
        request = lastfm.requests[0]
        self.assertEqual(request.params["autocorrect"], 0)
        self.assertIn("venue-db-event-check/1.0", request.headers["User-Agent"])

    def test_no_such_artist(self):
        self.assertIsNone(FakeLastFm().client().artist_info("DJ Maltese"))

    def test_top_track_and_album(self):
        lastfm = FakeLastFm(
            tracks={"157frq": fixture("top_tracks_157frq.json")},
            albums={("157frq", "Spine"): fixture("track_spine.json")},
        )
        self.assertEqual(lastfm.client().top_track("157frq"), {"name": "Spine", "album": "A World I Was Never a Part Of"})
        self.assertEqual(lastfm.methods, ["artist.getTopTracks", "track.getInfo"])

    def test_no_top_tracks(self):
        lastfm = FakeLastFm(tracks={"Nobody": fixture("no_top_tracks.json")})
        self.assertIsNone(lastfm.client().top_track("Nobody"))

    def test_paced(self):
        lastfm = FakeLastFm()
        client = lastfm.client()
        for _ in range(3):
            client.artist_info("x")
        self.assertEqual(lastfm.sleeps, [MIN_SECONDS_BETWEEN_REQUESTS] * 2)

    def test_rate_limit_and_suspension_stop(self):
        for name in ("rate_limited.json", "suspended.json"):
            with self.subTest(name), self.assertRaises(LastFmStopped):
                FakeLastFm(pages={"x": fixture(name)}).client().artist_info("x")

    def test_key_out_of_errors(self):
        for answer in (response(500, {}), response(200, {"error": 10, "message": "Invalid API key"}), fixture("rate_limited.json")):
            with self.subTest(answer), self.assertRaises(LastFmError) as raised:
                FakeLastFm(pages={"x": answer}).client().artist_info("x")
            self.assertNotIn(TEST_KEY, str(raised.exception))
            self.assertNotIn("audioscrobbler", str(raised.exception))


class MusicBrainzArtistTestCase(SimpleTestCase):
    MBID = "9a709693-b4f8-4da9-8cc1-038c911a61be"

    def test_artist_with_links(self):
        web = FakeWeb(mb_artists={self.MBID: {
            "name": "Bonobo", "area": "United Kingdom", "begin_area": "Brighton",
            "urls": ["https://open.spotify.com/artist/0cmWgDlu9CwTgxPhf403hb", "https://music.apple.com/us/artist/bonobo/1785628"],
        }})
        found = web.music_ids().artist(self.MBID)
        self.assertEqual(found["name"], "Bonobo")
        self.assertEqual([a["name"] for a in found["areas"]], ["United Kingdom", "Brighton"])
        self.assertEqual((found["spotify"], found["apple"]), ({"0cmWgDlu9CwTgxPhf403hb"}, {"1785628"}))

    def test_area_subdivision_by_part_of_links(self):
        web = FakeWeb()
        ids = web.music_ids()
        self.assertEqual(ids.area_subdivision(area_id("Somerville")), "US-MA")
        self.assertEqual(ids.area_subdivision(area_id("Massachusetts")), "US-MA")
        # Windsor, Ontario: named like Windsor, CT, but in Canada
        self.assertEqual(ids.area_subdivision(area_id("Windsor")), "CA-ON")
        requests = len(web.requests)
        self.assertEqual(ids.area_subdivision(area_id("Somerville")), "US-MA")
        self.assertEqual(len(web.requests), requests, "looked up once per run")
        self.assertEqual(ids.area_subdivision(area_id("Nowhere at all")), "")

    def test_artist_without_links(self):
        web = FakeWeb(mb_artists={self.MBID: {"name": "Bonobo"}})
        self.assertEqual(web.music_ids().artist(self.MBID), {"name": "Bonobo", "areas": [], "spotify": set(), "apple": set()})

    def test_unknown_or_malformed(self):
        web = FakeWeb()
        self.assertIsNone(web.music_ids().artist(self.MBID))
        self.assertIsNone(web.music_ids().artist("not-an-mbid"))

    def test_outage(self):
        from core.music_ids import MusicBrainzBusy

        with self.assertRaises(MusicBrainzBusy):
            FakeWeb(musicbrainz_503s=10).music_ids().artist(self.MBID)


class EvidenceRulesTestCase(TestCase):
    def setUp(self):
        Venue.objects.create(name="Sally O'Brien's", state="MA", city_town="Somerville")
        Venue.objects.create(name="Space Ballroom", state="CT", city_town="Hamden")
        self.places = covered_places()

    def test_covered_places(self):
        self.assertEqual(self.places, {"states": {"MA": "Massachusetts", "CT": "Connecticut"}, "towns": {"Somerville", "Hamden"}})

    def test_places_that_match(self):
        for text in ("Massachusetts", "a rapper from Western Massachusetts.", "a band from Worcester, MA", "formed in Hamden, CT in 2010"):
            with self.subTest(text):
                self.assertTrue(names_covered_place(text, self.places))

    def test_places_that_dont(self):
        # a covered town alone doesn't count: towns are also surnames ("Johnson", VT)
        for text in ("Brighton", "Germany", "United Kingdom", "Red Bank, NJ", "Massachusettsian", "Somerville", "with drummer Hamden Jones", "", None):
            with self.subTest(text):
                self.assertFalse(names_covered_place(text, self.places))

    def test_covered_subdivisions(self):
        self.assertTrue(is_covered_subdivision("US-MA", self.places))
        self.assertTrue(is_covered_subdivision("US-CT", self.places))
        for code in ("US-NJ", "CA-ON", "GB-ENG", "MA", "", None):
            with self.subTest(code):
                self.assertFalse(is_covered_subdivision(code, self.places))

    def test_shared_name_notes(self):
        for bio in (
            "There are at least two bands using the name Better Days.",
            "There are several bands called Dead Weight:",
            "There's 2 groups called Bars: 1) Introducing BARS 2) a punk band",
            "There are 2 artists with this name",
            "1) A ska band from Ohio. 2) A rapper.",
        ):
            with self.subTest(bio):
                self.assertTrue(shares_name(bio))
        self.assertFalse(shares_name("Simon Green, known by his stage name Bonobo, is a British musician."))

    def test_dominant(self):
        self.assertTrue(is_dominant(2_121_800, "a British musician"))
        self.assertTrue(is_dominant(100_000, ""))
        self.assertFalse(is_dominant(99_999, ""))
        self.assertFalse(is_dominant(500_000, "There are several bands called this."))
