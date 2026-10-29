import io
import json
import os
import tempfile
from unittest import mock

from core.artist_import import import_rows, parse_members, rows_from_csv
from core.management.commands import sync_venues_from_gsheets as sync
from core.models import Artist, Band, BandMembership, JobRun
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

HEADER = "Act_ID,Name,Kind,Members,Town,State,Website,Bandcamp,MusicBrainz_ID,Notes\n"
KRILL = 'A0001,Krill,band,"Jonah Furman (bass, vocals); Aaron Mendelsohn (guitar)",Boston,ma,https://krill.example,https://krill.bandcamp.com,,\n'
MBID = "6c0a0a64-5f63-4b9c-9f3a-4d0f1f3c2b11"


def rows(*lines):
    return rows_from_csv(io.StringIO(HEADER + "".join(lines)))


class ParseMembersTestCase(SimpleTestCase):
    def test_names_and_roles(self):
        self.assertEqual(
            parse_members("Jonah Furman (bass, vocals);  Aaron  Mendelsohn ; ;Ben Grigg (drums)"),
            [("Jonah Furman", "bass, vocals"), ("Aaron Mendelsohn", ""), ("Ben Grigg", "drums")],
        )
        self.assertEqual(parse_members(""), [])


class ImportArtistsTestCase(TestCase):
    def test_importing_a_band_with_members(self):
        report = import_rows(rows(KRILL))
        band = Band.objects.get(act_id="A0001")
        self.assertEqual((band.name, band.city_town, band.state), ("Krill", "Boston", "MA"))
        self.assertEqual(band.bandcamp_url, "https://krill.bandcamp.com")
        members = {(m.artist.name, m.role, m.source) for m in band.memberships.select_related("artist")}
        self.assertEqual(members, {("Jonah Furman", "bass, vocals", "import"), ("Aaron Mendelsohn", "guitar", "import")})
        self.assertEqual((len(report.created), len(report.members_added), report.problems), (1, 2, []))

    def test_importing_again(self):
        import_rows(rows(KRILL))
        before = list(Band.objects.values()), list(Artist.objects.values()), list(BandMembership.objects.values())
        report = import_rows(rows(KRILL))
        after = list(Band.objects.values()), list(Artist.objects.values()), list(BandMembership.objects.values())
        self.assertEqual([(k, v) for k, v in report.summary() if v], [("unchanged", 1)])
        # nothing changed but the update times, which a no-op import doesn't touch
        self.assertEqual(before, after)

    def test_an_editors_change_is_kept(self):
        import_rows(rows(KRILL))
        Band.objects.filter(act_id="A0001").update(website="https://krill.band", field_sources={"website": "editor"})
        import_rows(rows(KRILL))
        self.assertEqual(Band.objects.get(act_id="A0001").website, "https://krill.band")

    def test_musicbrainzs_values_are_kept(self):
        import_rows(rows(KRILL.replace("https://krill.example", "")))
        Band.objects.filter(act_id="A0001").update(
            website="https://from.musicbrainz", musicbrainz_id=MBID, field_sources={"website": "musicbrainz", "musicbrainz_id": "musicbrainz"}
        )
        import_rows(rows(KRILL))
        band = Band.objects.get(act_id="A0001")
        self.assertEqual((band.website, band.musicbrainz_id), ("https://from.musicbrainz", MBID))

    def test_a_bad_row(self):
        report = import_rows(rows("A0002,Orchestra Thing,orchestra,,,,,,,\n", KRILL, ",No ID,band,,,,,,,\n"))
        self.assertEqual([(n, problem) for n, _, problem in report.problems], [
            (2, "Kind 'orchestra' isn't artist or band; row skipped"),
            (4, "no Act_ID; row skipped"),
        ])
        self.assertEqual(list(Band.objects.values_list("name", flat=True)), ["Krill"])

    def test_not_a_bandcamp_url(self):
        report = import_rows(rows(KRILL.replace("https://krill.bandcamp.com", "https://example.com/krill")))
        band = Band.objects.get(act_id="A0001")
        self.assertEqual(band.bandcamp_url, "")
        self.assertEqual(band.website, "https://krill.example")
        self.assertEqual(report.problems, [(2, "A0001", "Bandcamp 'https://example.com/krill' isn't a bandcamp.com page; not saved")])

    def test_invalid_values_are_reported(self):
        line = "A0003,Solo Person,artist,,Providence,Rhode Island,not a url,,abc,\n"
        report = import_rows(rows(line))
        artist = Artist.objects.get(act_id="A0003")
        self.assertEqual((artist.state, artist.website, artist.musicbrainz_id), ("", "", None))
        self.assertEqual(len(report.problems), 3)

    def test_members_are_matched_not_duplicated(self):
        import_rows(rows(KRILL, 'A0004,Jonah Furman,artist,,Boston,MA,,,,\n', 'A0005,Other Band,band,Jonah Furman (vocals),,,,,,\n'))
        # the member made for krill takes his own row's Act_ID, and is the same person in the
        # other band
        jonah = Artist.objects.get(name="Jonah Furman")
        self.assertEqual(jonah.act_id, "A0004")
        self.assertEqual(set(jonah.bands.values_list("name", flat=True)), {"Krill", "Other Band"})

    def test_two_people_with_one_name_arent_merged(self):
        Artist.objects.create(name="Jon Smith")
        Artist.objects.create(name="Jon Smith")
        import_rows(rows("A0006,Jon Smith,artist,,,,,,,\n"))
        self.assertEqual(Artist.objects.filter(name="Jon Smith").count(), 3)

    def test_a_changed_role_updates_the_imports_membership(self):
        import_rows(rows(KRILL))
        import_rows(rows(KRILL.replace("(guitar)", "(guitar, vocals)")))
        roles = list(BandMembership.objects.filter(artist__name="Aaron Mendelsohn").values_list("role", flat=True))
        self.assertEqual(roles, ["guitar, vocals"])

    def test_memberships_from_others_are_kept(self):
        import_rows(rows(KRILL))
        band = Band.objects.get(act_id="A0001")
        BandMembership.objects.create(band=band, artist=Artist.objects.create(name="Ben Grigg"), role="drums", source="musicbrainz")
        import_rows(rows(KRILL))
        self.assertEqual(band.memberships.count(), 3)

    def test_kind_cant_change(self):
        import_rows(rows(KRILL))
        report = import_rows(rows(KRILL.replace(",band,", ",artist,")))
        self.assertEqual(report.problems[0][2], "A0001 is already a band; row skipped")

    def test_a_musicbrainz_id_from_the_sheet(self):
        import_rows(rows(KRILL.replace(",,\n", f",{MBID},\n")))
        band = Band.objects.get(act_id="A0001")
        self.assertEqual((band.musicbrainz_id, band.musicbrainz_status), (MBID, ""))

    def test_dry_run_saves_nothing(self):
        report = import_rows(rows(KRILL), dry_run=True)
        self.assertEqual(len(report.created), 1)
        self.assertEqual((Band.objects.count(), Artist.objects.count()), (0, 0))


class ImportArtistsCommandTestCase(TestCase):
    """import_artists, from a csv file or a sheet tab (gog and the service account mocked)"""

    VALUES = [
        ["Act_ID", "Name", "Kind", "Members", "Town", "State"],
        ["A0001", "Krill", "band", "Jonah Furman (bass)", "Boston", "MA"],
        ["A0002", "Solo", "artist"],
    ]

    def call(self, *args):
        out = io.StringIO()
        call_command("import_artists", *args, stdout=out)
        return out.getvalue()

    def test_from_a_csv_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as file:
            file.write(HEADER + KRILL)
        self.addCleanup(os.unlink, file.name)
        output = self.call("--csv", file.name)
        self.assertIn("A0001 Krill", output)
        self.assertEqual(Band.objects.get().memberships.count(), 2)
        run = JobRun.objects.latest("pk")
        self.assertEqual((run.command, run.status), ("import_artists", JobRun.Status.SUCCEEDED))
        self.assertIn(["created", 1], run.summary)

    def test_from_a_sheet_with_gog(self):
        with mock.patch.dict(os.environ, {}, clear=False) as env, mock.patch.object(
            sync.subprocess, "run", return_value=mock.Mock(stdout=json.dumps(self.VALUES))
        ) as run:
            env.pop("GOOGLE_SERVICE_ACCOUNT_JSON", None)
            self.call("--sheet", "sheet-id", "--tab", "Acts")
        self.assertEqual(run.call_args.args[0][:4], ["gog", "sheets", "get", "sheet-id"])
        self.assertIn("'Acts'!A1:ZZ", run.call_args.args[0])
        self.assertEqual(set(Band.objects.values_list("name", flat=True)), {"Krill"})
        self.assertTrue(Artist.objects.filter(act_id="A0002").exists())

    def test_from_a_sheet_with_the_service_account(self):
        with mock.patch.object(sync.google_sheets, "is_configured", return_value=True), mock.patch.object(
            sync.google_sheets, "read_values", return_value=self.VALUES
        ) as read:
            self.call("--sheet", "sheet-id", "--tab", "Acts")
        read.assert_called_once_with("sheet-id", "'Acts'!A1:ZZ", "Acts")
        self.assertTrue(Band.objects.filter(act_id="A0001").exists())

    def test_dry_run_saves_nothing(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as file:
            file.write(HEADER + KRILL)
        self.addCleanup(os.unlink, file.name)
        output = self.call("--csv", file.name, "--dry-run")
        self.assertIn("created [dry run, not saved] (1)", output)
        self.assertEqual((Band.objects.count(), Artist.objects.count()), (0, 0))

    def test_needs_one_source_and_the_key_columns(self):
        with self.assertRaisesMessage(CommandError, "give either --csv or --sheet"):
            self.call()
        with self.assertRaisesMessage(CommandError, "--sheet needs --tab"):
            self.call("--sheet", "sheet-id")
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as file:
            file.write("Name,Town\nKrill,Boston\n")
        self.addCleanup(os.unlink, file.name)
        with self.assertRaisesMessage(CommandError, "missing columns: Act_ID, Kind"):
            self.call("--csv", file.name)
