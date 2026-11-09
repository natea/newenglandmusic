import csv
import io

from core.admin_group import GROUP_NAME, sync_admin_group
from core.models import Venue, VenueEventSource
from core.venue_export import HEADER, NOT_EXPORTED, VENUE_COLUMNS, venue_row
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone


def row_dict(venue):
    return dict(zip(HEADER, venue_row(venue)))


class VenueRowTestCase(TestCase):
    def test_sheet_fields_in_the_row(self):
        venue = Venue.objects.create(
            name="Paradise", city_town="Boston", genres=["Funk", "Jazz"], open_booking=True,
            latitude=42.35, longitude=-71.06,
        )
        row = row_dict(venue)
        self.assertEqual(row["name"], "Paradise")
        self.assertEqual(row["city_town"], "Boston")
        self.assertEqual(row["genres"], "Funk; Jazz")
        self.assertEqual(row["open_booking"], "yes")
        self.assertEqual(row["longitude"], -71.06)

    def test_unknown_flag_is_blank(self):
        venue = Venue.objects.create(name="X", open_booking=None, open_mic=False)
        row = row_dict(venue)
        self.assertEqual(row["open_booking"], "")
        self.assertEqual(row["open_mic"], "no")

    def test_event_source_included(self):
        checked = Venue.objects.create(name="Checked")
        VenueEventSource.objects.create(
            venue=checked, checked_at=timezone.now(), best_source="ical", ical_url="https://example.com/cal.ics"
        )
        never = Venue.objects.create(name="Never")
        row = row_dict(Venue.objects.get(pk=checked.pk))
        self.assertEqual(row["best_source"], "ical")
        self.assertEqual(row["calendar_feed_url"], "https://example.com/cal.ics")
        row = row_dict(Venue.objects.get(pk=never.pk))
        self.assertEqual(row["best_source"], "")
        self.assertEqual(row["calendar_feed_url"], "")

    def test_confident_match_has_no_google_coordinates(self):
        venue = Venue.objects.create(
            name="Confident", latitude=1.5, longitude=2.5, place_id="ChIJabc",
            place_lookup_status=Venue.PlaceLookupStatus.CONFIDENT,
            place_latitude=42.123456, place_longitude=-71.654321, place_distance_km=0.7,
            place_looked_up_at=timezone.now(),
        )
        row = row_dict(venue)
        self.assertEqual(row["place_id"], "ChIJabc")
        self.assertEqual(row["place_lookup_status"], "confident")
        self.assertEqual((row["latitude"], row["longitude"]), (1.5, 2.5))
        flat = " ".join(str(v) for v in venue_row(venue))
        for secret in ("42.123456", "-71.654321", "0.7"):
            self.assertNotIn(secret, flat)
        self.assertEqual(len(venue_row(venue)), len(HEADER))

    def test_formula_like_note_gets_an_apostrophe(self):
        note = '=HYPERLINK("http://example.com")'
        row = row_dict(Venue.objects.create(name="X", booking_notes=note))
        self.assertEqual(row["booking_notes"], "'" + note)
        for start in ("+1", "-1", "@x", "\tx", "\rx"):
            self.assertEqual(row_dict(Venue.objects.create(name="Y", booking_notes=start))["booking_notes"], "'" + start)

    def test_commas_and_line_breaks_stay_in_one_row(self):
        notes = "Call ahead, ask for Sam\nthen wait"
        venue = Venue.objects.create(name="X", booking_notes=notes)
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(HEADER)
        writer.writerow(venue_row(venue))
        rows = list(csv.reader(io.StringIO(out.getvalue())))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][HEADER.index("booking_notes")], notes)


class FieldCoverageTestCase(TestCase):
    def test_every_venue_field_is_exported_or_excluded(self):
        fields = {f.name for f in Venue._meta.concrete_fields}
        undecided = fields - set(VENUE_COLUMNS) - NOT_EXPORTED
        self.assertEqual(undecided, set(), "export these Venue fields or name them in NOT_EXPORTED")
        self.assertEqual(set(VENUE_COLUMNS) - fields, set())


class ExportViewTestCase(TestCase):
    url = "/admin/core/venue/export-csv/"

    def setUp(self):
        self.admin = User.objects.create_superuser("admin", "a@example.com", "pw")
        self.client.force_login(self.admin)

    def rows(self, response):
        body = b"".join(response.streaming_content).decode("utf-8-sig")
        return list(csv.reader(io.StringIO(body)))

    def test_export_everything(self):
        for name in ("A", "B", "C"):
            Venue.objects.create(name=name)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertRegex(response["Content-Disposition"], r'attachment; filename="venues-\d{4}-\d\d-\d\d\.csv"')
        rows = self.rows(response)
        self.assertEqual(rows[0], HEADER)
        self.assertEqual([r[HEADER.index("name")] for r in rows[1:]], ["A", "B", "C"])

    def test_export_a_filtered_list(self):
        Venue.objects.create(name="A", is_active=True, state="MA")
        Venue.objects.create(name="B", is_active=True, state="MA")
        Venue.objects.create(name="C", is_active=False, state="MA")
        rows = self.rows(self.client.get(self.url, {"is_active__exact": "1"}))
        self.assertEqual(len(rows), 3)
        self.assertEqual({r[1] for r in rows[1:]}, {"A", "B"})

    def test_export_a_searched_list(self):
        Venue.objects.create(name="Paradise Rock Club")
        Venue.objects.create(name="Sinclair")
        rows = self.rows(self.client.get(self.url, {"q": "paradise"}))
        self.assertEqual([r[1] for r in rows[1:]], ["Paradise Rock Club"])

    def test_more_venues_than_a_page(self):
        Venue.objects.bulk_create(Venue(name=f"Venue {i:03}") for i in range(250))
        self.assertEqual(len(self.rows(self.client.get(self.url))), 251)

    def test_opens_in_excel(self):
        Venue.objects.create(name="Café Lena")
        response = self.client.get(self.url)
        body = b"".join(response.streaming_content)
        self.assertTrue(body.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Café Lena".encode("utf-8"), body)

    def test_signed_out_visitor_goes_to_login(self):
        Venue.objects.create(name="Secret Venue")
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
        self.assertNotIn(b"Secret Venue", response.content)

    def test_staff_without_permission_is_refused(self):
        Venue.objects.create(name="Secret Venue")
        staff = User.objects.create_user("staff", "s@example.com", "pw", is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"Secret Venue", response.content)

    def test_member_of_the_admin_group_can_download(self):
        sync_admin_group()
        Venue.objects.create(name="A")
        staff = User.objects.create_user("editor", "e@example.com", "pw", is_staff=True)
        staff.groups.add(Group.objects.get(name=GROUP_NAME))
        self.client.force_login(staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.rows(response)), 2)
