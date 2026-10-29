import json
from io import StringIO
from unittest import mock

from core.artist_enrichment import Matcher, enrich, links, members
from core.management.commands import enrich_artists_from_musicbrainz as command
from core.models import Artist, Band, BandMembership, JobRun, MusicAct
from core.music_ids import MUSICBRAINZ_SECONDS_BETWEEN_REQUESTS, MusicIds
from core.tests.musicbrainz_fixture import SPEEDY_ORTIZ, FakeLastFm, FakeMusicBrainz, candidate, details, load
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

Status = MusicAct.MusicBrainzStatus
HORSE_A, HORSE_B = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"
MA, LEEDS = "area-providence", "area-leeds"


class MusicBrainzClientTestCase(SimpleTestCase):
    """the requests core.music_ids.MusicIds makes for artist search and lookup"""

    def musicbrainz_client(self, *answers):
        session = mock.Mock()
        session.get.side_effect = [mock.Mock(status_code=200, json=mock.Mock(return_value=a)) for a in answers]
        self.sleeps, self.now = [], [100.0]
        ids = MusicIds(session=session, sleep=self.sleeps.append, clock=lambda: self.now[0])
        return ids, session

    def test_search_quotes_and_escapes_the_name(self):
        ids, session = self.musicbrainz_client(load("search-speedy-ortiz"))
        found = ids.search_artists('AC/DC: "Live"', "group")
        self.assertEqual(found[0]["id"], SPEEDY_ORTIZ)
        args, kwargs = session.get.call_args
        self.assertEqual(args[0], "https://musicbrainz.org/ws/2/artist")
        self.assertEqual(kwargs["params"]["query"], 'artist:"AC\\/DC\\: \\"Live\\"" AND type:group')
        self.assertEqual(kwargs["params"]["fmt"], "json")
        self.assertIn("venue-db-event-check/1.0", kwargs["headers"]["User-Agent"])

    def test_lookup_asks_for_members_links_and_genres(self):
        ids, session = self.musicbrainz_client(load("artist-speedy-ortiz"))
        self.assertEqual(ids.artist_details(SPEEDY_ORTIZ)["name"], "Speedy Ortiz")
        args, kwargs = session.get.call_args
        self.assertEqual(args[0], f"https://musicbrainz.org/ws/2/artist/{SPEEDY_ORTIZ}")
        self.assertEqual(kwargs["params"]["inc"], "artist-rels+url-rels+genres+aliases")
        # an id that isn't one is never sent
        self.assertIsNone(ids.artist_details("../area"))

    def test_paced(self):
        ids, session = self.musicbrainz_client({"artists": []}, {"artists": []})
        ids.search_artists("A", "group")
        ids.search_artists("B", "group")
        self.assertEqual(len(self.sleeps), 1)
        self.assertAlmostEqual(self.sleeps[0], MUSICBRAINZ_SECONDS_BETWEEN_REQUESTS)


class ParsingTestCase(SimpleTestCase):
    def test_links(self):
        found = links(load("artist-speedy-ortiz"))
        self.assertEqual(found["website"], "https://speedyortiz.com/")
        self.assertEqual(found["bandcamp_url"], "https://speedyortiz.bandcamp.com/")
        self.assertEqual(found["discogs_url"], "https://www.discogs.com/artist/2847690")

    def test_members(self):
        found = {m["name"]: m["role"] for m in members(load("artist-speedy-ortiz"))}
        self.assertEqual(len(found), 6)
        # "original" is how they joined, not a role
        self.assertEqual(found["Sadie Dupuis"], "banjo, cello, guitar, lead vocals, piano")


class MatcherTestCase(TestCase):
    def match(self, band, mb, lastfm=None):
        return Matcher(mb, lastfm=lastfm, covered_states={"US-MA", "US-RI"}).choose(band)

    def test_a_clear_match(self):
        band = Band.objects.create(name="Speedy Ortiz", state="MA")
        self.assertEqual(self.match(band, FakeMusicBrainz()), (Status.MATCHED, SPEEDY_ORTIZ))

    def test_only_the_same_name_and_kind(self):
        mb = FakeMusicBrainz(searches={"Horse": [candidate(HORSE_A, "Crazy Horse"), candidate(HORSE_B, "Horse", kind="Person")]})
        self.assertEqual(self.match(Band.objects.create(name="Horse"), mb), (Status.NOT_FOUND, None))

    def test_a_lone_namesake_elsewhere_isnt_accepted(self):
        mb = FakeMusicBrainz(searches={"Horse": [candidate(HORSE_A, "Horse", country="GB")]})
        self.assertEqual(self.match(Band.objects.create(name="Horse", state="MA"), mb), (Status.NOT_FOUND, None))
        mb = FakeMusicBrainz(searches={"Horse": [candidate(HORSE_A, "Horse", area_id=LEEDS)]}, areas={LEEDS: "GB-LDS"})
        self.assertEqual(self.match(Band.objects.create(name="Horse", state="RI"), mb), (Status.NOT_FOUND, None))

    def test_a_name_several_acts_share(self):
        mb = FakeMusicBrainz(searches={"Horse": [candidate(HORSE_A, "Horse"), candidate(HORSE_B, "Horse")]})
        self.assertEqual(self.match(Band.objects.create(name="Horse"), mb, FakeLastFm()), (Status.AMBIGUOUS, None))

    def test_a_covered_area_picks_the_candidate(self):
        mb = FakeMusicBrainz(
            searches={"Horse": [candidate(HORSE_A, "Horse", area_id=LEEDS), candidate(HORSE_B, "Horse", area_id=MA)]},
            areas={LEEDS: "GB-LDS", MA: "US-RI"},
        )
        self.assertEqual(self.match(Band.objects.create(name="Horse"), mb), (Status.MATCHED, HORSE_B))

    def test_lastfm_picks_the_candidate(self):
        mb = FakeMusicBrainz(searches={"Horse": [candidate(HORSE_A, "Horse"), candidate(HORSE_B, "Horse")]})
        lastfm = FakeLastFm({"Horse": {"mbid": HORSE_A, "listeners": 900, "bio": "Horse are a band."}})
        self.assertEqual(self.match(Band.objects.create(name="Horse"), mb, lastfm), (Status.MATCHED, HORSE_A))
        # but not when its page says several acts share the name
        lastfm.pages["Horse"]["bio"] = "There are at least two bands called Horse."
        self.assertEqual(self.match(Band.objects.create(name="Horse"), mb, lastfm), (Status.AMBIGUOUS, None))

    def test_without_lastfm(self):
        mb = FakeMusicBrainz(searches={"Horse": [candidate(HORSE_A, "Horse"), candidate(HORSE_B, "Horse")]})
        self.assertEqual(self.match(Band.objects.create(name="Horse"), mb, None), (Status.AMBIGUOUS, None))

    def test_an_alias_matches(self):
        mb = FakeMusicBrainz(searches={"SO": [candidate(SPEEDY_ORTIZ, "Speedy Ortiz", aliases=["SO"])]})
        self.assertEqual(self.match(Band.objects.create(name="SO"), mb), (Status.MATCHED, SPEEDY_ORTIZ))


class EnrichTestCase(TestCase):
    def enrich(self, record, mb=None, lastfm=None):
        mb = mb or FakeMusicBrainz()
        return enrich(record, mb, Matcher(mb, lastfm=lastfm, covered_states={"US-MA"}))

    def test_a_clear_match_stores_its_data_and_members(self):
        band = Band.objects.create(name="Speedy Ortiz", state="MA")
        status, added = self.enrich(band)
        band.refresh_from_db()
        self.assertEqual((status, band.musicbrainz_id), (Status.MATCHED, SPEEDY_ORTIZ))
        self.assertEqual((band.mb_type, band.country, band.area, band.begin_date), ("Group", "US", "United States", "2011"))
        # most votes first
        self.assertEqual(set(band.genres), {"alternative rock", "indie rock", "noise pop"})
        self.assertEqual((band.website, band.bandcamp_url), ("https://speedyortiz.com/", "https://speedyortiz.bandcamp.com/"))
        self.assertEqual(band.field_sources, {"musicbrainz_id": "musicbrainz", "website": "musicbrainz", "bandcamp_url": "musicbrainz"})
        self.assertEqual(len(added), 6)
        sadie = band.memberships.get(artist__name="Sadie Dupuis")
        self.assertEqual((sadie.source, sadie.artist.musicbrainz_id is not None), ("musicbrainz", True))
        self.assertIsNotNone(band.musicbrainz_checked_at)

    def test_the_records_own_links_stay(self):
        band = Band.objects.create(name="Speedy Ortiz", website="https://our.site", field_sources={"website": "import"})
        self.enrich(band)
        band.refresh_from_db()
        self.assertEqual(band.website, "https://our.site")
        self.assertEqual(band.bandcamp_url, "https://speedyortiz.bandcamp.com/")

    def test_a_name_several_acts_share_stores_nothing(self):
        mb = FakeMusicBrainz(searches={"Horse": [candidate(HORSE_A, "Horse"), candidate(HORSE_B, "Horse")]})
        band = Band.objects.create(name="Horse")
        self.assertEqual(self.enrich(band, mb), (Status.AMBIGUOUS, []))
        band.refresh_from_db()
        self.assertEqual((band.musicbrainz_id, band.genres, band.area), (None, [], ""))
        self.assertNotIn(("lookup", HORSE_A), mb.calls)

    def test_an_id_given_in_the_import_is_looked_up_not_searched(self):
        band = Band.objects.create(name="Speedy O.", musicbrainz_id=SPEEDY_ORTIZ, field_sources={"musicbrainz_id": "import"})
        mb = FakeMusicBrainz()
        self.enrich(band, mb)
        self.assertEqual(mb.calls, [("lookup", SPEEDY_ORTIZ)])
        band.refresh_from_db()
        self.assertEqual((band.musicbrainz_status, band.field_sources["musicbrainz_id"]), (Status.MATCHED, "import"))

    def test_an_editors_id_stays_the_editors(self):
        band = Band.objects.create(name="Speedy O.", musicbrainz_id=SPEEDY_ORTIZ, musicbrainz_status=Status.EDITOR)
        self.enrich(band)
        band.refresh_from_db()
        self.assertEqual((band.musicbrainz_id, band.musicbrainz_status), (SPEEDY_ORTIZ, Status.EDITOR))

    def test_members_already_known_are_linked_not_duplicated(self):
        sadie_id = next(m["id"] for m in members(load("artist-speedy-ortiz")) if m["name"] == "Sadie Dupuis")
        sadie = Artist.objects.create(name="Sadie Dupuis", musicbrainz_id=sadie_id)
        darl = Artist.objects.create(name="Darl Ferm")
        band = Band.objects.create(name="Speedy Ortiz")
        BandMembership.objects.create(band=band, artist=darl, role="bass", source="import")
        self.enrich(band)
        self.assertEqual(Artist.objects.filter(name="Sadie Dupuis").count(), 1)
        self.assertTrue(band.memberships.filter(artist=sadie).exists())
        # the import's membership stays as it is, with musicbrainz's id now on the artist
        self.assertEqual(list(band.memberships.filter(artist=darl).values_list("role", "source")), [("bass", "import")])
        self.assertIsNotNone(Artist.objects.get(pk=darl.pk).musicbrainz_id)

    def test_an_artist_already_linked_elsewhere(self):
        Band.objects.create(name="Speedy Ortiz (old)", musicbrainz_id=SPEEDY_ORTIZ)
        band = Band.objects.create(name="Speedy Ortiz")
        self.assertEqual(self.enrich(band), (Status.AMBIGUOUS, []))

    def test_an_id_musicbrainz_no_longer_knows(self):
        band = Band.objects.create(name="Gone", musicbrainz_id=HORSE_A)
        self.assertEqual(self.enrich(band)[0], Status.NOT_FOUND)


class EnrichCommandTestCase(TestCase):
    def run_command(self, *args, mb=None, lastfm=None, key="KEY"):
        mb = mb or FakeMusicBrainz()
        out = StringIO()
        with mock.patch.object(command, "MusicIds", return_value=mb), mock.patch.object(
            command.lastfm, "api_key", return_value=key
        ), mock.patch.object(command.lastfm, "client", return_value=lastfm or FakeLastFm()):
            call_command("enrich_artists_from_musicbrainz", *args, stdout=out)
        return out.getvalue(), mb

    def test_records_and_members(self):
        Band.objects.create(name="Speedy Ortiz")
        output, _ = self.run_command()
        self.assertIn(f"band Speedy Ortiz: matched {SPEEDY_ORTIZ}, members added:", output)
        run = JobRun.objects.latest("pk")
        self.assertIn(["matched", 1], run.summary)
        self.assertIn(["members added", 6], run.summary)

    def test_checked_records_are_skipped_unless_refreshing(self):
        Band.objects.create(name="Speedy Ortiz")
        self.run_command()
        # the second run looks up the members the first made, not the band again
        _, mb = self.run_command()
        self.assertNotIn(("lookup", SPEEDY_ORTIZ), mb.calls)
        self.assertNotIn(("search", "Speedy Ortiz", "group"), mb.calls)
        _, mb = self.run_command("--refresh", "--limit", "1")
        self.assertEqual(mb.calls, [("lookup", SPEEDY_ORTIZ)])

    def test_dry_run_saves_nothing(self):
        Band.objects.create(name="Speedy Ortiz")
        output, _ = self.run_command("--dry-run")
        self.assertIn("would record (1 records)", output)
        band = Band.objects.get()
        self.assertEqual((band.musicbrainz_id, band.musicbrainz_checked_at, Artist.objects.count()), (None, None, 0))

    def test_nothing_from_lastfm_is_saved(self):
        mb = FakeMusicBrainz(searches={"Horse": [candidate(HORSE_A, "Horse"), candidate(HORSE_B, "Horse")]}, artists={HORSE_A: details(HORSE_A, "Horse")})
        bio = "Horse are a Providence band with 4321 listeners and a distinctive bio."
        lastfm = FakeLastFm({"Horse": {"mbid": HORSE_A, "listeners": 4321, "bio": bio}})
        Band.objects.create(name="Horse")
        self.run_command(mb=mb, lastfm=lastfm)
        self.assertEqual(lastfm.calls, ["Horse"])
        stored = json.dumps(list(Band.objects.values()), default=str)
        for text in ("distinctive bio", "4321", "last.fm"):
            self.assertNotIn(text, stored)
        self.assertEqual(Band.objects.get().musicbrainz_id, HORSE_A)

    def test_without_a_lastfm_key(self):
        mb = FakeMusicBrainz(searches={"Horse": [candidate(HORSE_A, "Horse"), candidate(HORSE_B, "Horse")]})
        Band.objects.create(name="Horse")
        output, _ = self.run_command(mb=mb, key=None)
        self.assertIn("LASTFM_API_KEY isn't set", output)
        self.assertEqual(Band.objects.get().musicbrainz_status, Status.AMBIGUOUS)

    def test_no_request_goes_to_bandcamp(self):
        Band.objects.create(name="Speedy Ortiz")
        with mock.patch("requests.Session.request", side_effect=AssertionError("no requests")) as request, mock.patch(
            "requests.get", side_effect=AssertionError("no requests")
        ):
            self.run_command()
        request.assert_not_called()
        self.assertEqual(Band.objects.get().bandcamp_url, "https://speedyortiz.bandcamp.com/")

    def test_musicbrainz_busy_stops_the_run_and_keeps_what_was_saved(self):
        from core.music_ids import MusicBrainzBusy

        Band.objects.create(name="Speedy Ortiz")
        Band.objects.create(name="Zzz")
        mb = FakeMusicBrainz()
        original = mb.search_artists

        def search(name, kind):
            if name == "Zzz":
                raise MusicBrainzBusy("musicbrainz: HTTP 503 after 4 tries")
            return original(name, kind)

        mb.search_artists = search
        output, _ = self.run_command(mb=mb)
        self.assertIn("stopping this run", output)
        self.assertEqual(Band.objects.get(name="Speedy Ortiz").musicbrainz_id, SPEEDY_ORTIZ)
