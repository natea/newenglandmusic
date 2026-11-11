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

    def test_filtering_by_source(self):
        Band.objects.create(name="'Til Tuesday", sources=["ohb"])
        Band.objects.create(name="Dropkick Murphys", musicbrainz_status=Status.MATCHED, sources=["ohb"])
        url = reverse("admin:core_band_changelist")
        response = self.client.get(url + "?source=ohb")
        self.assertEqual({b.name for b in response.context["cl"].result_list}, {"'Til Tuesday", "Dropkick Murphys"})
        self.assertContains(response, "Oh Hello Boston")
        # with no filter, every band, the source shown only where there is one
        self.assertEqual(len(self.client.get(url).context["cl"].result_list), 3)

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


class ClearingAMatchKeepsHubDataTestCase(TestCase):
    def test_clearing_a_match(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        finding = {"field": "website", "current": "", "hub": "https://krill.example.com", "seen_at": "2026-11-01T00:00:00+00:00", "dismissed": False}
        band = Band.objects.create(
            name="Krill", musicbrainz_id=OTHER, instagram_url="https://www.instagram.com/hubfill/",
            link_hub_url="https://linktr.ee/krill", link_hub_findings=[finding],
            field_sources={"instagram_url": "link hub", "link_hub_url": "musicbrainz", "musicbrainz_id": "musicbrainz"},
        )
        self.client.post(reverse("admin:core_band_changelist"), {"action": "clear_musicbrainz_match", "_selected_action": [band.pk]})
        band.refresh_from_db()
        self.assertEqual(band.instagram_url, "https://www.instagram.com/hubfill/")
        self.assertEqual((band.link_hub_url, band.link_hub_findings), ("https://linktr.ee/krill", [finding]))
        self.assertEqual(band.field_sources, {"instagram_url": "link hub", "link_hub_url": "musicbrainz"})


def finding(field, current, hub, **extra):
    return {"field": field, "current": current, "hub": hub, "seen_at": "2026-11-01T00:00:00+00:00", "dismissed": False, **extra}


class LinkHubAdminTestCase(TestCase):
    YOUTUBE = finding("youtube_url", "https://www.youtube.com/@krill", "https://www.youtube.com/channel/UC123")

    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))

    def records(self):
        """one of each kind, with an open youtube finding"""
        return [
            model.objects.create(
                name="Krill", link_hub_url="https://linktr.ee/krill", youtube_url="https://www.youtube.com/@krill",
                link_hub_findings=[self.YOUTUBE], link_hub_status="read",
            )
            for model in (Band, Artist)
        ]

    def action(self, record, name):
        url = reverse(f"admin:core_{record._meta.model_name}_changelist")
        return self.client.post(url, {"action": name, "_selected_action": [record.pk]}, follow=True)

    def test_the_change_page_shows_the_hub_status_and_findings(self):
        for record in self.records():
            html = self.client.get(reverse(f"admin:core_{record._meta.model_name}_change", args=[record.pk])).content.decode()
            self.assertIn("Link hub", html)
            self.assertIn("https://linktr.ee/krill", html)
            self.assertIn("hub: https://www.youtube.com/channel/UC123", html)
            self.assertIn("now: https://www.youtube.com/@krill", html)

    def test_not_a_page_on_a_hub(self):
        for record in self.records():
            for address in ("https://linktr.ee/", "https://example.com/links"):
                data = form_data(record, link_hub_url=address)
                response = self.client.post(reverse(f"admin:core_{record._meta.model_name}_change", args=[record.pk]), data)
                self.assertContains(response, "a page on a supported link hub")
                record.refresh_from_db()
                self.assertEqual(record.link_hub_url, "https://linktr.ee/krill")

    def test_an_editors_address_is_theirs_and_is_read_next(self):
        for record in self.records():
            data = form_data(record, link_hub_url="http://beacons.ai/krillband?x=1", website="")
            response = self.client.post(reverse(f"admin:core_{record._meta.model_name}_change", args=[record.pk]), data)
            self.assertEqual(response.status_code, 302)
            record.refresh_from_db()
            self.assertEqual((record.link_hub_url, record.field_sources["link_hub_url"]), ("https://beacons.ai/krillband", "editor"))
            self.assertEqual((record.link_hub_status, record.link_hub_checked_at), ("", None))

    def test_the_address_can_be_cleared(self):
        for record in self.records():
            response = self.client.post(reverse(f"admin:core_{record._meta.model_name}_change", args=[record.pk]), form_data(record, link_hub_url=""))
            self.assertEqual(response.status_code, 302)
            record.refresh_from_db()
            self.assertEqual(record.link_hub_url, "")

    def test_the_read_only_fields_are_not_marked_as_the_editors(self):
        for record in self.records():
            data = form_data(record, link_hub_url=record.link_hub_url, instagram_url="", youtube_url=record.youtube_url)
            self.client.post(reverse(f"admin:core_{record._meta.model_name}_change", args=[record.pk]), data)
            record.refresh_from_db()
            for name in ("link_hub_status", "link_hub_checked_at", "link_hub_findings"):
                self.assertNotIn(name, record.field_sources)
            self.assertEqual((record.link_hub_status, record.link_hub_findings), ("read", [self.YOUTUBE]))

    def test_accepting_a_finding(self):
        for record in self.records():
            response = self.action(record, "accept_link_hub_findings")
            self.assertContains(response, "1 findings accepted.")
            record.refresh_from_db()
            self.assertEqual(record.youtube_url, "https://www.youtube.com/channel/UC123")
            self.assertEqual(record.field_sources["youtube_url"], "editor")
            self.assertEqual(record.link_hub_findings, [])

    def test_a_finding_with_several_candidates_is_left_for_the_editor(self):
        several = finding("instagram_url", "", "https://www.instagram.com/a/", options=["https://www.instagram.com/a/", "https://www.instagram.com/b/"])
        band = Band.objects.create(name="Krill", link_hub_findings=[several, self.YOUTUBE])
        response = self.action(band, "accept_link_hub_findings")
        self.assertContains(response, "1 with several candidates left open")
        band.refresh_from_db()
        self.assertEqual((band.instagram_url, band.youtube_url), ("", "https://www.youtube.com/channel/UC123"))
        self.assertEqual(band.link_hub_findings, [several])

    def test_dismissing_a_finding(self):
        for record in self.records():
            response = self.action(record, "dismiss_link_hub_findings")
            self.assertContains(response, "1 findings dismissed.")
            record.refresh_from_db()
            self.assertEqual(record.youtube_url, "https://www.youtube.com/@krill")
            self.assertEqual([f["dismissed"] for f in record.link_hub_findings], [True])

    def test_records_with_findings(self):
        for model in (Band, Artist):
            with_finding = model.objects.create(name="Krill", link_hub_findings=[self.YOUTUBE])
            model.objects.create(name="Horse", link_hub_findings=[{**self.YOUTUBE, "dismissed": True}])
            model.objects.create(name="Pile")
            url = reverse(f"admin:core_{model._meta.model_name}_changelist")
            listed = self.client.get(url, {"link_hub_findings": "1"}).context["cl"].result_list
            self.assertEqual([a.pk for a in listed], [with_finding.pk])
            everyone = self.client.get(url).context["cl"].result_list
            self.assertEqual(len(everyone), 3)

    def test_the_list_counts_open_findings(self):
        Band.objects.create(name="Krill", link_hub_findings=[self.YOUTUBE, finding("website", "", "https://krill.example.com")])
        html = self.client.get(reverse("admin:core_band_changelist")).content.decode()
        self.assertIn('<td class="field-link_hub_findings_count">2</td>', html)
