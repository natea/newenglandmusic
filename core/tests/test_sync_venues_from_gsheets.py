import json
import subprocess
from io import StringIO
from unittest import mock

from core.management.commands import sync_venues_from_gsheets as sync
from core.models import Event, Venue
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

# the sheet's columns, as read by venue_fields_from_row
COLUMNS = [
    "Venue_Location_Name",
    "Map_State",
    "Map_City_Town",
    "Map_County",
    "Map_Latitude",
    "Map_Longitude",
    "Venue_Is_Active",
    "Venue_Type",
    "Venue_Size",
    "Venue_Genre_Notes",
    "Venue_Genre_Search",
    "Venue_Niche_Notes",
    "Venue_Open_Booking",
    "Venue_Booking_Type",
    "Venue_Open_Mic",
    "Venue_URL",
    "Venue_Booking_URL",
    "Venue_Booking_Notes",
    "Access_Age",
    "Access_Notes",
    "Access_Family_Friendly",
    "Access_LGBTQ+",
    "Access_Diverse",
    "Access_Safety",
    "Access_Safety_URL",
    "Access_Safety_Notes",
    "Venue_ID",
]


def row(venue_id, name, **values):
    """a sheet row with every column, blank unless given"""
    result = dict.fromkeys(COLUMNS, "")
    result.update({"Venue_ID": venue_id, "Venue_Location_Name": name}, **values)
    return result


class ParseValuesTestCase(SimpleTestCase):
    def test_parse_yes_no(self):
        for value in ("Y", "y", "Yes", " YES "):
            self.assertIs(sync.parse_yes_no(value), True, value)
        for value in ("N", "no", " No"):
            self.assertIs(sync.parse_yes_no(value), False, value)
        # anything uncertain is unknown, not false
        for value in ("", "Maybe?", "???", "sometimes"):
            self.assertIsNone(sync.parse_yes_no(value), value)

    def test_parse_float(self):
        self.assertEqual(sync.parse_float("42.36"), 42.36)
        self.assertEqual(sync.parse_float("-71.1"), -71.1)
        self.assertIsNone(sync.parse_float(""))
        self.assertIsNone(sync.parse_float("n/a"))

    def test_parse_size(self):
        self.assertEqual(sync.parse_size("Small (<100)"), "small")
        self.assertEqual(sync.parse_size("medium (<500)"), "medium")
        self.assertEqual(sync.parse_size(" Large (500+)"), "large")
        self.assertEqual(sync.parse_size(""), "")
        self.assertEqual(sync.parse_size("Huge"), "")

    def test_parse_genres(self):
        self.assertEqual(sync.parse_genres("Funk; Jazz;"), ["Funk", "Jazz"])
        self.assertEqual(sync.parse_genres("ALL"), ["ALL"])
        self.assertEqual(sync.parse_genres(" ; "), [])
        self.assertEqual(sync.parse_genres(""), [])

    def test_booking_type_labels_map_to_choices(self):
        fields = sync.venue_fields_from_row(row("V1", "v", Venue_Booking_Type="submit a show"))
        self.assertEqual(fields["booking_type"], Venue.BookingType.SUBMIT_SHOW)
        fields = sync.venue_fields_from_row(row("V1", "v", Venue_Booking_Type="Nope"))
        self.assertEqual(fields["booking_type"], "")

    def test_state_is_two_upper_case_letters(self):
        fields = sync.venue_fields_from_row(row("V1", "v", Map_State="ma "))
        self.assertEqual(fields["state"], "MA")


class GetRowsTestCase(SimpleTestCase):
    def run_gog(self, **kwargs):
        with mock.patch.object(sync.subprocess, "run", **kwargs) as run:
            return sync.get_rows_from_google_sheets("sheet-id", "Tab"), run

    def test_rows_are_padded_to_the_header(self):
        output = json.dumps([["a", "b", "c"], ["1"], ["1", "2", "3"]])
        rows, run = self.run_gog(return_value=mock.Mock(stdout=output))
        self.assertEqual(rows, [{"a": "1", "b": "", "c": ""}, {"a": "1", "b": "2", "c": "3"}])
        self.assertEqual(run.call_args.args[0][:4], ["gog", "sheets", "get", "sheet-id"])
        self.assertIn("'Tab'!A1:ZZ", run.call_args.args[0])

    def test_gog_not_installed(self):
        with self.assertRaisesMessage(CommandError, "gog cli is not installed"):
            self.run_gog(side_effect=FileNotFoundError)

    def test_gog_fails(self):
        error = subprocess.CalledProcessError(1, "gog", stderr="token expired\n")
        with self.assertRaisesMessage(CommandError, "gog failed: token expired"):
            self.run_gog(side_effect=error)


class SyncCommandTestCase(TestCase):
    def sync(self, rows, *args):
        out = StringIO()
        with mock.patch.object(sync, "get_rows_from_google_sheets", return_value=rows):
            call_command("sync_venues_from_gsheets", *args, stdout=out)
        return out.getvalue()

    def test_new_row_creates_venue(self):
        output = self.sync(
            [
                row(
                    "V0001",
                    "The Middle East",
                    Map_State="MA",
                    Map_City_Town="Cambridge",
                    Map_Latitude="42.3634",
                    Map_Longitude="-71.1013",
                    Venue_Is_Active="Y",
                    Venue_Size="Medium (<500)",
                    Venue_Genre_Search="Rock; Punk;",
                    Venue_Booking_Type="Submit an Artist",
                    Access_Family_Friendly="Maybe?",
                    Venue_URL="https://mideastoffers.com",
                )
            ]
        )
        venue = Venue.objects.get(sheet_id="V0001")
        self.assertEqual(venue.name, "The Middle East")
        self.assertEqual(venue.location, "Cambridge, MA")
        self.assertEqual((venue.latitude, venue.longitude), (42.3634, -71.1013))
        self.assertIs(venue.is_active, True)
        self.assertEqual(venue.size, "medium")
        self.assertEqual(venue.genres, ["Rock", "Punk"])
        self.assertEqual(venue.booking_type, Venue.BookingType.SUBMIT_ARTIST)
        self.assertIsNone(venue.family_friendly)
        self.assertEqual(venue.website, "https://mideastoffers.com")
        self.assertIn("created 1 venues, updated 0 venues", output)

    def test_edited_row_updates_venue_in_place(self):
        self.sync([row("V0001", "Old Name", Map_State="MA")])
        venue = Venue.objects.get(sheet_id="V0001")

        output = self.sync([row("V0001", "New Name", Map_State="NH")])

        self.assertEqual(Venue.objects.count(), 1)
        venue.refresh_from_db()
        self.assertEqual((venue.name, venue.state), ("New Name", "NH"))
        self.assertIn("created 0 venues, updated 1 venues", output)

    def test_same_name_with_different_ids_stays_separate(self):
        rows = [
            row("V0572", "Arlene's Grocery", Map_State="NY", Map_City_Town="New York"),
            row("V0573", "Arlene's Grocery", Map_State="NY", Map_City_Town="New York"),
        ]
        self.sync(rows)
        self.sync(rows)
        self.assertEqual(Venue.objects.filter(name="Arlene's Grocery").count(), 2)

    def test_missing_venue_id_column_fails(self):
        rows = [{"Venue_Location_Name": "v"}]
        with self.assertRaisesMessage(CommandError, "no Venue_ID column"):
            self.sync(rows)
        self.assertFalse(Venue.objects.exists())

    def test_duplicate_venue_id_fails_and_saves_nothing(self):
        Venue.objects.create(sheet_id="V0001", name="Before")
        rows = [row("V0001", "After"), row("V0002", "New"), row("V0002", "Again")]
        with self.assertRaisesMessage(CommandError, "row 4: Venue_ID V0002 is used more than once"):
            self.sync(rows)
        # the whole sync rolled back
        self.assertEqual(Venue.objects.get(sheet_id="V0001").name, "Before")
        self.assertFalse(Venue.objects.filter(sheet_id="V0002").exists())

    def test_row_without_id_is_skipped_with_warning(self):
        output = self.sync([row("", "No ID Bar"), row("V0002", "Has ID"), row("", "")])
        self.assertFalse(Venue.objects.filter(name="No ID Bar").exists())
        self.assertTrue(Venue.objects.filter(sheet_id="V0002").exists())
        self.assertIn("row 2: no Venue_ID, skipping", output)
        # fully blank rows are skipped silently
        self.assertNotIn("row 4", output)

    def test_venue_removed_from_sheet_is_kept_and_reported(self):
        self.sync([row("V0001", "Stays"), row("V0002", "Gone From Sheet")])
        output = self.sync([row("V0001", "Stays")])
        self.assertTrue(Venue.objects.filter(sheet_id="V0002").exists())
        self.assertIn("not in sheet (left as is): Gone From Sheet [V0002]", output)

    def test_unknown_booking_type_warns(self):
        output = self.sync([row("V0001", "v", Venue_Booking_Type="Bribes Only")])
        self.assertEqual(Venue.objects.get(sheet_id="V0001").booking_type, "")
        self.assertIn("row 2: unknown booking type 'Bribes Only'", output)

    def test_dry_run_saves_nothing(self):
        Venue.objects.create(sheet_id="V0001", name="Before")
        output = self.sync([row("V0001", "After"), row("V0002", "New")], "--dry-run")
        self.assertIn("[dry run] created 1 venues, updated 1 venues", output)
        self.assertEqual(Venue.objects.get(sheet_id="V0001").name, "Before")
        self.assertFalse(Venue.objects.filter(sheet_id="V0002").exists())

    def test_sync_leaves_the_ticketmaster_link_alone(self):
        Venue.objects.create(sheet_id="V0001", name="Before", ticketmaster_venue_id="KovZpZA11JtA")
        self.sync([row("V0001", "After")])
        venue = Venue.objects.get(sheet_id="V0001")
        self.assertEqual(venue.name, "After")
        self.assertEqual(venue.ticketmaster_venue_id, "KovZpZA11JtA")

    def test_fields_not_in_the_sheet_are_preserved(self):
        venue = Venue.objects.create(
            sheet_id="V0001", name="Before", website="https://example.com", is_active=True
        )
        event = Event.objects.create(title="show", starttime=timezone.now(), venue=venue)

        # a sheet that only maps the name, so every other field is "not in the sheet"
        with mock.patch.object(
            sync, "venue_fields_from_row", lambda r: {"name": r["Venue_Location_Name"]}
        ):
            self.sync([row("V0001", "After")])

        venue.refresh_from_db()
        self.assertEqual(venue.name, "After")
        self.assertEqual(venue.website, "https://example.com")
        self.assertIs(venue.is_active, True)
        # updated in place: same row, its events still attached
        self.assertEqual(Venue.objects.get(sheet_id="V0001").pk, venue.pk)
        self.assertEqual(Event.all_objects.get(pk=event.pk).venue_id, venue.pk)
