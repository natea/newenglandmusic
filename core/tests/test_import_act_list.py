import csv
import os
import tempfile
from io import StringIO
from unittest import mock

from core.act_list import state_code
from core.management.commands import import_act_list as command
from core.models import Artist, Band, Event, JobRun, Venue
from core.tests.musicbrainz_fixture import FakeLastFm, FakeMusicBrainz, candidate, details
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

HEADER = ["Artist", "Genre", "City", "State", "Tracks on Air", "Active?", "Website", "Bandcamp", "Instagram", "YouTube", "Kind", "MusicBrainz ID"]
TIL_TUESDAY = "8cf8869d-e066-4c94-b734-fe05749badf0"
TAURUS = "b578d762-d262-41a6-a981-a31dc04121eb"
SHERMAN = "7644da0b-0252-497f-aef1-21cd77ddb68a"
DOLLS = "11111111-1111-4111-8111-111111111111"
HORSE_P, HORSE_G = "22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333"
DROPKICK = "44444444-4444-4444-8444-444444444444"
SUNBURST = "55555555-5555-4555-8555-555555555555"
TWENTY7 = "36dc09e7-93da-4c23-bc0d-dcb68c8ed74f"
UNTYPED = "66666666-6666-4666-8666-666666666666"
SEARCHES = {
    "28 Degrees Taurus": [candidate(TAURUS, "28 Degrees Taurus")],
    "Horse": [candidate(HORSE_P, "Horse", kind="Person"), candidate(HORSE_G, "Horse")],
    "Adam Sherman": [candidate(SHERMAN, "Adam Sherman", kind="Person")],
    "The Dresden Dolls": [candidate(DOLLS, "The Dresden Dolls")],
    "Dresden Dolls": [candidate(DOLLS, "The Dresden Dolls")],
    "Sunburst": [candidate(SUNBURST, "Sunburst", area_id="ohio")],
}
ARTISTS = {
    TIL_TUESDAY: details(TIL_TUESDAY, "'Til Tuesday", "Group"),
    SHERMAN: details(SHERMAN, "Adam Sherman", "Person"),
    SUNBURST: details(SUNBURST, "Sunburst", "Group", area={"id": "ohio", "name": "Ohio"}),
    TWENTY7: details(TWENTY7, "Twenty Seven Strings", "Group"),
    UNTYPED: details(UNTYPED, "Wire Lines", None),
}


def row(name, city="", state="", website="", bandcamp="", instagram="", youtube="", kind="", mbid=""):
    return [name, "", city, state, "1", "Yes", website, bandcamp, instagram, youtube, kind, mbid]


class StateCodeTestCase(SimpleTestCase):
    def test_state_names(self):
        self.assertEqual([state_code(s) for s in ("Massachusetts", "ma", "Rhode Island", "")], ["MA", "MA", "RI", ""])


class ImportActListTestCase(TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        # the site covers the states it has venues in: here, massachusetts
        self.venue = Venue.objects.create(sheet_id="V0001", name="O'Brien's", city_town="Allston", state="MA")

    def tab(self, name, *rows):
        path = os.path.join(self.dir, f"{name}.csv")
        with open(path, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(HEADER)
            writer.writerows(rows)
        return path

    def run_command(self, *tabs, dry_run=False):
        self.mb = FakeMusicBrainz(searches=SEARCHES, artists=ARTISTS, areas={"ohio": "US-OH"})
        args = ["--source", "ohb"]
        for path in tabs:
            args += ["--csv", path]
        if dry_run:
            args.append("--dry-run")
        out = StringIO()
        with mock.patch.object(command, "MusicIds", return_value=self.mb), mock.patch.object(
            command.lastfm, "api_key", return_value="KEY"
        ), mock.patch.object(command.lastfm, "client", return_value=FakeLastFm()):
            call_command("import_act_list", *args, stdout=out)
        return out.getvalue()

    def test_a_row_with_a_musicbrainz_id(self):
        self.run_command(self.tab("rotation", row("'Til Tuesday", "Boston", "Massachusetts", kind="Band", mbid=TIL_TUESDAY)))
        band = Band.objects.get(name="'Til Tuesday")
        self.assertEqual((band.musicbrainz_id, band.sources, band.state), (TIL_TUESDAY, ["ohb"], "MA"))
        self.assertEqual(self.mb.calls, [("lookup", TIL_TUESDAY)])
        self.assertFalse(band.needs_review)

    def test_a_row_found_by_name(self):
        self.run_command(self.tab("rotation", row("28 Degrees Taurus", "Boston", "Massachusetts", bandcamp="https://28degreestaurus.bandcamp.com/")))
        band = Band.objects.get(name="28 Degrees Taurus")
        self.assertEqual(
            (band.musicbrainz_id, band.city_town, band.state, band.bandcamp_url, band.sources),
            (TAURUS, "Boston", "MA", "https://28degreestaurus.bandcamp.com/", ["ohb"]),
        )
        self.assertEqual(band.field_sources["bandcamp_url"], "ohb")

    def test_both_kinds_settled_by_the_list(self):
        self.run_command(self.tab("rotation", row("Horse", kind="Band")))
        self.assertEqual(Band.objects.get(name="Horse").musicbrainz_id, HORSE_G)
        self.assertFalse(Artist.objects.filter(name="Horse").exists())

    def test_both_kinds_without_a_kind_are_held(self):
        self.run_command(self.tab("rotation", row("Horse")))
        horse = Band.objects.get(name="Horse")
        self.assertEqual((horse.needs_review, horse.review_reasons, horse.musicbrainz_id), (True, ["kind"], None))

    def test_not_on_musicbrainz(self):
        self.run_command(self.tab("rotation", row("3 1/2 Girls", website="https://example.org/girls")))
        band = Band.objects.get(name="3 1/2 Girls")
        self.assertEqual((band.needs_review, band.review_reasons, band.website, band.sources), (True, ["not_found"], "https://example.org/girls", ["ohb"]))

    def test_the_lists_kind_for_an_act_not_on_musicbrainz(self):
        self.run_command(self.tab("rotation", row("Zoe Knight", kind="Artist")))
        self.assertTrue(Artist.objects.get(name="Zoe Knight").needs_review)

    def test_matched_to_an_act_from_elsewhere(self):
        self.run_command(self.tab("rotation", row("Sunburst", "Boston", "Massachusetts")))
        band = Band.objects.get(name="Sunburst")
        self.assertEqual((band.musicbrainz_id, band.needs_review, band.review_reasons), (SUNBURST, True, ["elsewhere"]))

    def test_an_id_for_a_different_act(self):
        self.run_command(self.tab("rotation", row("27", mbid=TWENTY7)))
        self.assertEqual(Band.objects.get(name="27").review_reasons, ["name"])

    def test_an_act_with_no_type_on_musicbrainz_takes_the_lists_kind(self):
        self.run_command(self.tab("rotation", row("Wire Lines", kind="Band", mbid=UNTYPED)))
        band = Band.objects.get(name="Wire Lines")
        self.assertEqual((band.musicbrainz_id, band.needs_review), (UNTYPED, False))

    def test_a_dry_run(self):
        out = self.run_command(self.tab("rotation", row("28 Degrees Taurus"), row("3 1/2 Girls")), dry_run=True)
        self.assertFalse(Band.objects.exists())
        self.assertIn("made live 1", out)
        self.assertIn("held for review 1", out)

    def test_an_act_on_both_tabs(self):
        rotation = self.tab("rotation", row("Adam Sherman", "Boston", "Massachusetts", instagram="https://www.instagram.com/adam.sherman.music/", mbid=SHERMAN))
        backlog = self.tab("backlog", row("Adam Sherman", instagram="https://www.instagram.com/adamsherman/", youtube="https://www.youtube.com/@adamsherman6483", mbid=SHERMAN))
        out = self.run_command(rotation, backlog)
        artist = Artist.objects.get(name="Adam Sherman")
        self.assertEqual(Artist.objects.filter(name="Adam Sherman").count(), 1)
        # looked up once, the first tab's instagram kept, the second tab's youtube added
        self.assertEqual(self.mb.calls, [("lookup", SHERMAN)])
        self.assertEqual(artist.instagram_url, "https://www.instagram.com/adam.sherman.music/")
        self.assertEqual(artist.youtube_url, "https://www.youtube.com/@adamsherman6483")
        self.assertIn("gives Adam Sherman a different instagram_url", out)

    def test_a_name_repeated_on_one_tab(self):
        self.run_command(self.tab("rotation", row("The Dresden Dolls"), row("Dresden Dolls")))
        self.assertEqual(Band.objects.count(), 1)

    def test_a_list_names_an_act_made_from_events(self):
        dropkick = Band.objects.create(name="Dropkick Murphys", musicbrainz_id=DROPKICK, website="https://dropkickmurphys.com", field_sources={"website": "editor"})
        self.run_command(self.tab("rotation", row("Dropkick Murphys", "Quincy", "Massachusetts", website="https://example.org/dkm", mbid=DROPKICK)))
        self.assertEqual(Band.objects.filter(name="Dropkick Murphys").count(), 1)
        dropkick.refresh_from_db()
        # found, its source added, its empty town filled and its editor's website kept
        self.assertEqual((dropkick.sources, dropkick.city_town, dropkick.website), (["ohb"], "Quincy", "https://dropkickmurphys.com"))

    def test_importing_twice(self):
        tab = self.tab("rotation", row("28 Degrees Taurus"), row("'Til Tuesday", mbid=TIL_TUESDAY))
        self.run_command(tab)
        out = self.run_command(tab)
        self.assertEqual(Band.objects.count(), 2)
        self.assertEqual([b.sources for b in Band.objects.all()], [["ohb"], ["ohb"]])
        self.assertIn("made live 0", out)

    def test_existing_events_are_linked(self):
        venue = self.venue
        kim = Artist.objects.create(name="Kim Deal")
        event = Event.all_objects.create(
            title="", artists="28 Degrees Taurus, Kim Deal", starttime=timezone.now() + timezone.timedelta(days=3), venue=venue, is_approved=True
        )
        self.run_command(self.tab("rotation", row("28 Degrees Taurus")))
        self.assertEqual([p.act.name for p in event.performers.order_by("order")], ["28 Degrees Taurus", kim.name])

    def test_recorded_as_a_job_run(self):
        self.run_command(self.tab("rotation", row("28 Degrees Taurus")))
        self.assertEqual(JobRun.objects.latest("pk").command, "import_act_list")

    def test_a_live_act_stays_live(self):
        dropkick = Band.objects.create(name="Dropkick Murphys", musicbrainz_id=DROPKICK)
        # her row's id names a different act: a made record would be held, a found one isn't
        self.run_command(self.tab("rotation", row("Dropkick Murphys", mbid=TWENTY7)))
        dropkick.refresh_from_db()
        self.assertEqual((dropkick.needs_review, dropkick.sources), (False, ["ohb"]))


class HeldForReviewTestCase(TestCase):
    """an act held for review stays off the site until an editor marks it ready"""

    def setUp(self):
        self.venue = Venue.objects.create(sheet_id="V0001", name="O'Brien's", state="MA")
        self.band = Band.objects.create(name="3 1/2 Girls", needs_review=True, review_reasons=["not_found"], sources=["ohb"])
        self.event = Event.all_objects.create(
            title="", artists="3 1/2 Girls", starttime=timezone.now() + timezone.timedelta(days=3), venue=self.venue, is_approved=True
        )

    def test_hidden_while_held(self):
        from core.event_performers import link_from_names

        self.assertEqual(self.client.get(self.band.get_absolute_url()).status_code, 404)
        link_from_names(self.event)
        self.assertFalse(self.event.performers.exists())

    def test_marked_ready(self):
        from django.contrib.auth.models import User

        self.client.force_login(User.objects.create_superuser("admin", password="pw"))
        response = self.client.post(
            "/admin/core/band/", {"action": "mark_ready", "_selected_action": [self.band.pk]}, follow=True
        )
        self.assertContains(response, "1 marked ready; 1 events linked to them.")
        self.band.refresh_from_db()
        self.assertEqual((self.band.needs_review, self.band.review_reasons), (False, []))
        self.assertEqual(self.client.get(self.band.get_absolute_url()).status_code, 200)
        self.assertEqual([p.act for p in self.event.performers.all()], [self.band])

    def test_the_admin_lists_held_acts_with_their_reasons(self):
        from django.contrib.auth.models import User

        Band.objects.create(name="Krill")
        self.client.force_login(User.objects.create_superuser("admin", password="pw"))
        response = self.client.get("/admin/core/band/?needs_review__exact=1")
        self.assertEqual([b.name for b in response.context["cl"].result_list], ["3 1/2 Girls"])
        self.assertContains(response, "needs review: not on MusicBrainz")
