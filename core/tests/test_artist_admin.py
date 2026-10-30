from io import StringIO
from unittest import mock

from core.management.commands import enrich_artists_from_musicbrainz as command
from core.models import Artist, Band, BandMembership, MusicAct
from core.tests.musicbrainz_fixture import SPEEDY_ORTIZ, FakeLastFm, FakeMusicBrainz, fake_wikipedia
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

Status = MusicAct.MusicBrainzStatus
OTHER = "11111111-1111-4111-8111-111111111111"


def form_data(band, **changes):
    """the band admin's form as posted, with no members changed"""
    data = {
        "name": band.name, "slug": band.slug, "act_id": band.act_id or "", "city_town": band.city_town, "state": band.state,
        "website": band.website, "bandcamp_url": band.bandcamp_url, "notes": band.notes,
        "musicbrainz_id": band.musicbrainz_id or "",
        "memberships-TOTAL_FORMS": "0", "memberships-INITIAL_FORMS": "0",
        "memberships-MIN_NUM_FORMS": "0", "memberships-MAX_NUM_FORMS": "1000",
    }
    data.update(changes)
    return data


class ArtistAdminTestCase(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.band = Band.objects.create(name="Krill", state="MA", act_id="A0001", genres=["indie rock"])
        self.jonah = Artist.objects.create(name="Jonah Furman")
        BandMembership.objects.create(band=self.band, artist=self.jonah, role="bass", begin_year=2012, source="import")

    def change(self, record):
        return self.client.get(reverse(f"admin:core_{record._meta.model_name}_change", args=[record.pk]))

    def test_members_inline(self):
        html = self.change(self.band).content.decode()
        self.assertIn("Jonah Furman", html)
        self.assertIn('value="bass"', html)
        self.assertIn("2012", html)
        self.assertIn("Import", html)
        # and the artist's page lists the band
        self.assertIn("Krill", self.change(self.jonah).content.decode())

    def test_adding_a_member(self):
        sophie = Artist.objects.create(name="Sophie")
        data = form_data(self.band, **{
            "memberships-TOTAL_FORMS": "1", "memberships-0-artist": str(sophie.pk), "memberships-0-role": "drums",
            "memberships-0-band": str(self.band.pk),
        })
        response = self.client.post(reverse("admin:core_band_change", args=[self.band.pk]), data)
        self.assertEqual(response.status_code, 302, response.content.decode()[:2000])
        self.assertEqual(self.band.memberships.get(artist=sophie).source, BandMembership.Source.EDITOR)

    def test_edits_are_the_editors(self):
        response = self.client.post(
            reverse("admin:core_band_change", args=[self.band.pk]), form_data(self.band, website="https://krill.band")
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Band.objects.get(pk=self.band.pk).field_sources, {"website": "editor"})

    def test_setting_the_musicbrainz_id_by_hand(self):
        self.client.post(reverse("admin:core_band_change", args=[self.band.pk]), form_data(self.band, musicbrainz_id=SPEEDY_ORTIZ))
        band = Band.objects.get(pk=self.band.pk)
        self.assertEqual((band.musicbrainz_status, band.field_sources["musicbrainz_id"]), (Status.EDITOR, "editor"))
        # a refresh looks it up by that id, and keeps it as the editor's
        mb = FakeMusicBrainz()
        wikipedia, _ = fake_wikipedia()
        with mock.patch.object(command, "MusicIds", return_value=mb), mock.patch.object(command.lastfm, "api_key", return_value=None), mock.patch.object(
            command, "Wikipedia", return_value=wikipedia
        ):
            call_command("enrich_artists_from_musicbrainz", "--refresh", stdout=StringIO())
        band.refresh_from_db()
        self.assertEqual((band.musicbrainz_id, band.musicbrainz_status), (SPEEDY_ORTIZ, Status.EDITOR))
        self.assertIn(("lookup", SPEEDY_ORTIZ), mb.calls)
        self.assertNotIn(("search", "Krill", "group"), mb.calls)

    def test_not_a_musicbrainz_id(self):
        response = self.client.post(reverse("admin:core_band_change", args=[self.band.pk]), form_data(self.band, musicbrainz_id="krill"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("a MusicBrainz id", response.content.decode())

    def test_clearing_a_match(self):
        Band.objects.filter(pk=self.band.pk).update(
            musicbrainz_id=OTHER, musicbrainz_status=Status.MATCHED, area="Boston", bandcamp_url="https://krill.bandcamp.com",
            website="https://krill.example", field_sources={"musicbrainz_id": "musicbrainz", "bandcamp_url": "musicbrainz", "website": "import"},
        )
        self.client.post(reverse("admin:core_band_changelist"), {"action": "clear_musicbrainz_match", "_selected_action": [self.band.pk]})
        band = Band.objects.get(pk=self.band.pk)
        self.assertEqual((band.musicbrainz_id, band.musicbrainz_status, band.area, band.genres), (None, "", "", []))
        # musicbrainz's link goes, the import's stays
        self.assertEqual((band.bandcamp_url, band.website), ("", "https://krill.example"))
        self.assertEqual(band.field_sources, {"website": "import"})

    def test_list_filters_and_search(self):
        Band.objects.create(name="Speedy Ortiz", state="MA", musicbrainz_status=Status.AMBIGUOUS)
        Band.objects.create(name="Horse", state="RI")
        url = reverse("admin:core_band_changelist")
        names = lambda query: {b.name for b in self.client.get(url + query).context["cl"].result_list}
        self.assertEqual(names("?state=MA"), {"Krill", "Speedy Ortiz"})
        self.assertEqual(names("?musicbrainz_status__exact=ambiguous"), {"Speedy Ortiz"})
        self.assertEqual(names("?q=kri"), {"Krill"})

    def test_genres_are_credited(self):
        html = self.change(self.band).content.decode()
        self.assertIn("indie rock", html)
        self.assertIn("genres from <a href=\"https://musicbrainz.org/doc/About/Data_License\">MusicBrainz</a>, CC BY-NC-SA", html)


class IntroductionAdminTestCase(TestCase):
    def test_the_credit(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        band = Band.objects.create(
            name="Speedy Ortiz", wikipedia_extract="Speedy Ortiz is an American indie rock band.",
            wikipedia_url="https://en.wikipedia.org/wiki/Speedy_Ortiz", disambiguation="Northampton band",
        )
        html = self.client.get(reverse("admin:core_band_change", args=[band.pk])).content.decode()
        self.assertIn("Speedy Ortiz is an American indie rock band.", html)
        self.assertIn('From the Wikipedia article <a href="https://en.wikipedia.org/wiki/Speedy_Ortiz"', html)
        self.assertIn('<a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noopener">CC BY-SA 4.0</a>', html)
        self.assertIn("Northampton band", html)

    def test_clearing_a_match_clears_the_introduction(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        band = Band.objects.create(name="X", musicbrainz_id=OTHER, wikipedia_extract="text", wikipedia_url="https://en.wikipedia.org/wiki/X", disambiguation="d")
        self.client.post(reverse("admin:core_band_changelist"), {"action": "clear_musicbrainz_match", "_selected_action": [band.pk]})
        band.refresh_from_db()
        self.assertEqual((band.wikipedia_extract, band.wikipedia_url, band.disambiguation), ("", "", ""))


class PhotoAndLinksAdminTestCase(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))

    def test_photo_preview_and_links_on_the_page(self):
        band = Band.objects.create(
            name="Bonerama", photo_file="Bonerama2006.jpg", photo_author="Masahiro Sumori", photo_license="CC BY-SA 3.0",
            instagram_url="https://www.instagram.com/bonerama/",
        )
        html = self.client.get(reverse("admin:core_band_change", args=[band.pk])).content.decode()
        self.assertIn("https://commons.wikimedia.org/wiki/Special:FilePath/Bonerama2006.jpg?width=480", html)
        self.assertIn("https://www.instagram.com/bonerama/", html)

    def test_clearing_a_match_drops_its_photo_and_links_but_not_an_editors(self):
        band = Band.objects.create(
            name="Bonerama", musicbrainz_id=OTHER, photo_file="Bonerama2006.jpg", photo_license="CC BY-SA 3.0",
            instagram_url="https://www.instagram.com/x/", youtube_url="https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx",
            field_sources={"instagram_url": "musicbrainz", "youtube_url": "editor"},
        )
        self.client.post(reverse("admin:core_band_changelist"), {"action": "clear_musicbrainz_match", "_selected_action": [band.pk]})
        band.refresh_from_db()
        self.assertEqual((band.photo_file, band.photo_license, band.instagram_url), ("", "", ""))
        self.assertEqual(band.youtube_url, "https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx")
