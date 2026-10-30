import csv
import os
import tempfile
from io import StringIO
from unittest import mock

from core.artist_import import import_rows
from core.management.commands import import_artists_from_events as command
from core.models import Artist, Band, Event, EventPerformer, JobRun, Venue
from core.music_ids import MusicBrainzBusy
from core.tests.musicbrainz_fixture import SPEEDY_ORTIZ, FakeLastFm, FakeMusicBrainz, candidate
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

KIM, HORSE_P, HORSE_G = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333"
SEARCHES = {
    "Kim Deal": [candidate(KIM, "Kim Deal", kind="Person")],
    "Horse": [candidate(HORSE_P, "Horse", kind="Person"), candidate(HORSE_G, "Horse")],
}


class ImportArtistsFromEventsTestCase(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(sheet_id="V0001", name="Paradise", state="MA")
        directory = tempfile.mkdtemp()
        self.review = os.path.join(directory, "review.csv")

    def event(self, artists, approved=True, title=""):
        # no title by default: a title's names count too (test_a_headliner_in_the_title)
        return Event.all_objects.create(
            title=title, artists=artists, starttime=timezone.now(), venue=self.venue, is_approved=approved
        )

    def run_command(self, *args, mb=None):
        self.mb = mb or FakeMusicBrainz(searches=SEARCHES)
        out = StringIO()
        with mock.patch.object(command, "MusicIds", return_value=self.mb), mock.patch.object(
            command.lastfm, "api_key", return_value="KEY"
        ), mock.patch.object(command.lastfm, "client", return_value=FakeLastFm()):
            call_command("import_artists_from_events", "--review-csv", self.review, *args, stdout=out)
        return out.getvalue()

    def review_rows(self):
        with open(self.review, newline="") as file:
            return list(csv.DictReader(file))

    def test_a_band_and_a_person(self):
        event = self.event("Speedy Ortiz, Kim Deal")
        self.run_command()
        self.assertEqual(Band.objects.get(name="Speedy Ortiz").musicbrainz_id, SPEEDY_ORTIZ)
        kim = Artist.objects.get(name="Kim Deal")
        self.assertEqual((kim.musicbrainz_id, kim.act_id, kim.musicbrainz_status), (KIM, None, ""))
        # and the event is linked to both, in order
        self.assertEqual([p.act.name for p in event.performers.order_by("order")], ["Speedy Ortiz", "Kim Deal"])

    def test_both_a_person_and_a_group(self):
        self.event("Horse")
        self.run_command()
        self.assertFalse(Artist.objects.exists() or Band.objects.exists())
        row = self.review_rows()[0]
        self.assertEqual((row["Name"], row["Reason"], row["Kind"], row["Act_ID"]), ("Horse", "both a person and a group", "", ""))

    def test_not_on_musicbrainz(self):
        self.event("Dana and Alden")
        self.event("Dana and Alden, Kim Deal")
        self.run_command()
        row = next(r for r in self.review_rows() if r["Name"] == "Dana and Alden")
        self.assertEqual((row["Reason"], row["Events"]), ("not on MusicBrainz", "2"))
        self.assertIn("@ Paradise", row["Example_Event"])

    def test_placeholders_repeats_and_existing_records_arent_searched(self):
        Band.objects.create(name="Krill")
        self.event("TBA, Krill, Kim Deal")
        self.event("Kim Deal, krill")
        self.run_command()
        searched = {call[1] for call in self.mb.calls if call[0] == "search"}
        self.assertEqual(searched, {"Kim Deal"})

    def test_only_approved_events(self):
        self.event("Kim Deal", approved=False)
        self.run_command()
        self.assertEqual(self.mb.calls, [])
        self.assertFalse(Artist.objects.exists())

    def test_most_named_first(self):
        self.event("Horse")
        self.event("Kim Deal")
        self.event("Kim Deal")
        self.run_command("--limit", "1")
        self.assertEqual({call[1] for call in self.mb.calls}, {"Kim Deal"})

    def test_dry_run(self):
        event = self.event("Speedy Ortiz, Horse")
        output = self.run_command("--dry-run")
        self.assertIn("would make (2 names to look up)", output)
        self.assertFalse(Band.objects.exists())
        self.assertFalse(EventPerformer.objects.exists())
        self.assertEqual([r["Name"] for r in self.review_rows()], ["Horse"])

    def test_busy_musicbrainz_stops_and_keeps_what_was_made(self):
        self.event("Speedy Ortiz")
        self.event("Speedy Ortiz, Kim Deal")
        mb = FakeMusicBrainz(searches=SEARCHES)
        original = mb.search_artists

        def search(name, kind):
            if name == "Kim Deal":
                raise MusicBrainzBusy("musicbrainz: HTTP 503 after 4 tries")
            return original(name, kind)

        mb.search_artists = search
        output = self.run_command(mb=mb)
        self.assertIn("stopping this run", output)
        self.assertTrue(Band.objects.filter(name="Speedy Ortiz").exists())
        run = JobRun.objects.latest("pk")
        self.assertIn(["bands made", 1], run.summary)

    def test_the_review_list_imports(self):
        self.event("Horse, Dana and Alden")
        self.run_command()
        rows = self.review_rows()
        for number, row in enumerate(rows, start=1):
            row["Act_ID"], row["Kind"] = f"E{number:04d}", "band"
        report = import_rows(rows)
        self.assertEqual(report.problems, [])
        self.assertEqual(set(Band.objects.values_list("name", flat=True)), {"Horse", "Dana and Alden"})


class TitleNamesTestCase(ImportArtistsFromEventsTestCase):
    """every source puts the headliner in the title and leaves it out of the artists"""

    def test_a_headliner_in_the_title(self):
        event = self.event("Kim Deal", title="Speedy Ortiz")
        self.run_command()
        self.assertTrue(Band.objects.filter(name="Speedy Ortiz").exists())
        self.assertEqual([p.act.name for p in event.performers.order_by("order")], ["Speedy Ortiz", "Kim Deal"])

    def test_title_words_that_arent_names(self):
        self.event("", title="Halloween Party")
        self.event("", title="Open Mic Night")
        self.run_command()
        self.assertEqual(self.mb.calls, [])
