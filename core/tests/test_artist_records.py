from core.artists import is_bandcamp_url
from core.models import Artist, Band, BandMembership
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase


class ArtistRecordsTestCase(TestCase):
    def test_a_member_of_two_bands(self):
        artist = Artist.objects.create(name="Sophie Allison")
        krill = Band.objects.create(name="Krill")
        horse = Band.objects.create(name="Horse Jumper of Love")
        BandMembership.objects.create(band=krill, artist=artist, role="drums")
        BandMembership.objects.create(band=horse, artist=artist, role="vocals")
        self.assertEqual(set(artist.bands.values_list("name", flat=True)), {"Krill", "Horse Jumper of Love"})
        self.assertEqual(krill.memberships.get().role, "drums")
        self.assertEqual(horse.memberships.get().role, "vocals")

    def test_a_former_member(self):
        band = Band.objects.create(name="Krill")
        old = BandMembership.objects.create(band=band, artist=Artist.objects.create(name="A"), end_year=2019)
        current = BandMembership.objects.create(band=band, artist=Artist.objects.create(name="B"), begin_year=2012)
        self.assertTrue(old.is_former)
        self.assertFalse(current.is_former)

    def test_the_same_role_only_once(self):
        band, artist = Band.objects.create(name="Krill"), Artist.objects.create(name="A")
        BandMembership.objects.create(band=band, artist=artist, role="bass")
        BandMembership.objects.create(band=band, artist=artist, role="vocals")
        with self.assertRaises(IntegrityError), transaction.atomic():
            BandMembership.objects.create(band=band, artist=artist, role="bass")

    def test_name_key_and_blank_ids(self):
        band = Band.objects.create(name="The Krill!", act_id="", musicbrainz_id="")
        self.assertEqual(band.name_key, "krill")
        # blank ids are stored as none, so many records can lack one
        Band.objects.create(name="Other", act_id="", musicbrainz_id="")
        self.assertIsNone(band.act_id)
        self.assertIsNone(band.musicbrainz_id)

    def test_bandcamp_url_is_validated(self):
        band = Band(name="Krill", bandcamp_url="https://example.com/krill")
        with self.assertRaises(ValidationError):
            band.full_clean()
        Band(name="Krill", bandcamp_url="https://krill.bandcamp.com/").full_clean()


class BandcampUrlTestCase(SimpleTestCase):
    def test_bandcamp_urls(self):
        for url in ("https://krill.bandcamp.com", "https://bandcamp.com/krill", "https://krill.bandcamp.com/album/x"):
            self.assertTrue(is_bandcamp_url(url), url)
        for url in (
            "http://krill.bandcamp.com", "https://example.com/krill", "https://bandcamp.com.evil.example",
            "https://notbandcamp.com", "", None, "krill.bandcamp.com",
        ):
            self.assertFalse(is_bandcamp_url(url), url)
