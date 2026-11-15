import csv
import io
import re

from core.act_export import ACT_COLUMNS, ARTIST_HEADER, BAND_HEADER, NOT_EXPORTED, act_row, header, prefetch
from core.admin_group import GROUP_NAME, sync_admin_group
from core.models import Artist, Band, BandMembership
from django.contrib.auth.models import Group, Permission, User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext


def row_dict(act):
    model = type(act)
    act = prefetch(model.objects.filter(pk=act.pk)).get()
    return dict(zip(header(model), act_row(act)))


class ActRowTestCase(TestCase):
    def test_artist_fields_in_the_row(self):
        artist = Artist.objects.create(
            name="Kim", city_town="Boston", state="MA", musicbrainz_id="4fbf1a3d-a649-4f8e-9ddf-347f6ba2d307",
            act_id="A1", sources=["ohb", "x"], photo_author="Someone", photo_license="CC BY 2.0",
        )
        row = row_dict(artist)
        self.assertEqual(row["name"], "Kim")
        self.assertEqual(row["city_town"], "Boston")
        self.assertEqual(row["state"], "MA")
        self.assertEqual(row["musicbrainz_id"], "4fbf1a3d-a649-4f8e-9ddf-347f6ba2d307")
        self.assertEqual(row["act_id"], "A1")
        self.assertEqual(row["sources"], "ohb; x")
        self.assertEqual(row["photo_author"], "Someone")
        self.assertEqual(row["page"], "/artists/kim")
        self.assertEqual(len(act_row(artist)), len(ARTIST_HEADER))

    def test_band_members(self):
        band = Band.objects.create(name="Krill")
        bass = Artist.objects.create(name="Jonah Furman")
        other = Artist.objects.create(name="Aaron Mendelsohn")
        BandMembership.objects.create(band=band, artist=bass, role="bass", begin_year=2010)
        BandMembership.objects.create(band=band, artist=other, begin_year=2011)
        row = row_dict(band)
        self.assertEqual(row["members"], "Jonah Furman (bass); Aaron Mendelsohn")
        self.assertEqual(len(act_row(band)), len(BAND_HEADER))

    def test_an_artists_bands(self):
        artist = Artist.objects.create(name="Ilya")
        BandMembership.objects.create(band=Band.objects.create(name="Krill"), artist=artist, role="drums")
        BandMembership.objects.create(band=Band.objects.create(name="Mal Blum"), artist=artist)
        self.assertEqual(row_dict(artist)["bands"], "Krill (drums); Mal Blum")

    def test_held_act_shows_its_review_status_and_has_no_page(self):
        band = Band.objects.create(name="Held", needs_review=True, review_reasons=["not_found", "odd"])
        row = row_dict(band)
        self.assertEqual(row["needs_review"], "yes")
        self.assertEqual(row["review_reasons"], "not on MusicBrainz; odd")
        self.assertEqual(row["page"], "")

    def test_blank_values_are_blank(self):
        row = row_dict(Artist.objects.create(name="Plain"))
        for name in ("act_id", "city_town", "musicbrainz_id", "website", "bands", "sources"):
            self.assertEqual(row[name], "")
        self.assertEqual(row["needs_review"], "no")

    def test_credit_bound_and_bookkeeping_data_is_absent(self):
        act = Band.objects.create(
            name="Credited", genres=["math rock"], wikipedia_extract="Credited are a band from Boston.",
            wikipedia_url="https://en.wikipedia.org/wiki/Credited", wikipedia_revision="rev123",
            field_sources={"website": "editor"},
        )
        flat = " ".join(str(v) for v in act_row(prefetch(Band.objects.filter(pk=act.pk)).get()))
        for hidden in ("math rock", "are a band from Boston", "wikipedia.org", "rev123", "editor"):
            self.assertNotIn(hidden, flat)

    def test_formula_like_note_gets_an_apostrophe(self):
        note = '=HYPERLINK("http://example.com")'
        self.assertEqual(row_dict(Artist.objects.create(name="X", notes=note))["notes"], "'" + note)
        for start in ("+1", "-1", "@x", "\tx", "\rx"):
            self.assertEqual(row_dict(Artist.objects.create(name="Y", notes=start))["notes"], "'" + start)

    def test_commas_and_line_breaks_stay_in_one_row(self):
        notes = "Seen live, great\nsecond line"
        act = Band.objects.create(name="X", notes=notes)
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(BAND_HEADER)
        writer.writerow(act_row(prefetch(Band.objects.filter(pk=act.pk)).get()))
        rows = list(csv.reader(io.StringIO(out.getvalue())))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][BAND_HEADER.index("notes")], notes)


class FieldCoverageTestCase(TestCase):
    def test_every_act_field_is_exported_or_excluded(self):
        for model in (Artist, Band):
            fields = {f.name for f in model._meta.concrete_fields}
            undecided = fields - set(ACT_COLUMNS) - NOT_EXPORTED
            self.assertEqual(undecided, set(), f"export these {model.__name__} fields or name them in NOT_EXPORTED")
            self.assertEqual(set(ACT_COLUMNS) - fields, set())


class ExportViewTestCase(TestCase):
    """the admin's two lists, one test class for both kinds"""

    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))

    def rows(self, response):
        body = b"".join(response.streaming_content).decode("utf-8-sig")
        return list(csv.reader(io.StringIO(body)))

    def names(self, rows):
        return [r[1] for r in rows[1:]]

    def test_export_every_artist(self):
        for name in ("A", "B", "C"):
            Artist.objects.create(name=name)
        response = self.client.get("/admin/core/artist/export-csv/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertRegex(response["Content-Disposition"], r'attachment; filename="artists-\d{4}-\d\d-\d\d\.csv"')
        rows = self.rows(response)
        self.assertEqual(rows[0], ARTIST_HEADER)
        self.assertEqual(self.names(rows), ["A", "B", "C"])

    def test_band_filename_and_header(self):
        Band.objects.create(name="A")
        response = self.client.get("/admin/core/band/export-csv/")
        self.assertRegex(response["Content-Disposition"], r'attachment; filename="bands-\d{4}-\d\d-\d\d\.csv"')
        self.assertEqual(self.rows(response)[0], BAND_HEADER)

    def test_export_a_filtered_band_list(self):
        Band.objects.create(name="A", state="MA")
        Band.objects.create(name="B", state="MA")
        Band.objects.create(name="C", state="NY")
        rows = self.rows(self.client.get("/admin/core/band/export-csv/", {"state": "MA"}))
        self.assertEqual(self.names(rows), ["A", "B"])

    def test_export_a_searched_list(self):
        Artist.objects.create(name="Kim Gordon")
        Artist.objects.create(name="Sinéad")
        rows = self.rows(self.client.get("/admin/core/artist/export-csv/", {"q": "kim"}))
        self.assertEqual(self.names(rows), ["Kim Gordon"])

    def test_more_bands_than_a_page(self):
        Band.objects.bulk_create(Band(name=f"Band {i:03}", slug=f"band-{i:03}") for i in range(250))
        self.assertEqual(len(self.rows(self.client.get("/admin/core/band/export-csv/"))), 251)

    def test_held_acts_are_included(self):
        Band.objects.create(name="Live")
        Band.objects.create(name="Held", needs_review=True, review_reasons=["not_found"])
        rows = self.rows(self.client.get("/admin/core/band/export-csv/"))
        held = [r for r in rows[1:] if r[1] == "Held"][0]
        self.assertEqual(held[BAND_HEADER.index("needs_review")], "yes")
        self.assertEqual(len(rows), 3)

    def test_opens_in_excel(self):
        Artist.objects.create(name="Sinéad")
        body = b"".join(self.client.get("/admin/core/artist/export-csv/").streaming_content)
        self.assertTrue(body.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Sinéad".encode("utf-8"), body)

    def test_members_are_read_without_a_query_per_band(self):
        artist = Artist.objects.create(name="M")

        def queries(bands):
            for i in range(bands):
                BandMembership.objects.create(band=Band.objects.create(name=f"B{i}-{Band.objects.count()}"), artist=artist, role="bass")
            with CaptureQueriesContext(connection) as captured:
                body = b"".join(self.client.get("/admin/core/band/export-csv/").streaming_content)
            self.assertIn(b"M (bass)", body)
            return len(captured)

        self.assertEqual(queries(1), queries(5))

    def test_signed_out_visitor_goes_to_login(self):
        Artist.objects.create(name="Secret Artist")
        self.client.logout()
        response = self.client.get("/admin/core/artist/export-csv/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
        self.assertNotIn(b"Secret Artist", response.content)

    def test_view_permission_is_per_kind(self):
        Artist.objects.create(name="Secret Artist")
        Band.objects.create(name="Open Band")
        staff = User.objects.create_user("staff", "s@example.com", "pw", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename="view_band"))
        self.client.force_login(staff)
        response = self.client.get("/admin/core/artist/export-csv/")
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"Secret Artist", response.content)
        self.assertNotContains(self.client.get("/admin/core/band/"), "Secret Artist")
        self.assertEqual(self.client.get("/admin/core/band/export-csv/").status_code, 200)

    def test_member_of_the_admin_group_can_download(self):
        sync_admin_group()
        Band.objects.create(name="A")
        staff = User.objects.create_user("editor", "e@example.com", "pw", is_staff=True)
        staff.groups.add(Group.objects.get(name=GROUP_NAME))
        self.client.force_login(staff)
        response = self.client.get("/admin/core/band/export-csv/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.rows(response)), 2)


class ExportButtonTestCase(TestCase):
    def test_button_keeps_the_filter_query_string(self):
        Band.objects.create(name="A", state="MA")
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        html = self.client.get("/admin/core/band/", {"state": "MA", "q": "A"}).content.decode()
        match = re.search(r'<a href="([^"]*)" class="export-csv"', html)
        self.assertTrue(match.group(1).startswith("/admin/core/band/export-csv/?"))
        self.assertIn("state=MA", match.group(1))
        self.assertIn("q=A", match.group(1))

    def test_each_list_links_to_its_own_export(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.assertContains(self.client.get("/admin/core/artist/"), 'href="/admin/core/artist/export-csv/')
        self.assertContains(self.client.get("/admin/core/band/"), 'href="/admin/core/band/export-csv/')

    def test_no_button_without_view_permission(self):
        staff = User.objects.create_user("staff", "s@example.com", "pw", is_staff=True)
        staff.user_permissions.add(Permission.objects.get(codename="view_band"))
        self.client.force_login(staff)
        self.assertEqual(self.client.get("/admin/core/artist/").status_code, 403)
        self.assertNotContains(self.client.get("/admin/core/artist/"), "Export to CSV", status_code=403)
        self.assertContains(self.client.get("/admin/core/band/"), "Export to CSV")
