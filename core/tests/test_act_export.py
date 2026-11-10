import csv
import io

from core.act_export import ACT_COLUMNS, ARTIST_HEADER, BAND_HEADER, NOT_EXPORTED, act_row, header, prefetch
from core.models import Artist, Band, BandMembership
from django.test import TestCase


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
