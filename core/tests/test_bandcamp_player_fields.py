from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from core.artists import bandcamp_player_url
from core.models import Artist, Band

KRILL = "https://krill.bandcamp.com/"


def found(**fields):
    values = dict(
        name="Krill", bandcamp_url=KRILL, bandcamp_embed_kind="album", bandcamp_embed_id="1234567890",
        bandcamp_embed_status="found", bandcamp_embed_for=KRILL,
    )
    return Band.objects.create(**{**values, **fields})


class BandcampPlayerAddressTestCase(SimpleTestCase):
    def test_player_address_from_an_album_id(self):
        url = bandcamp_player_url("album", "1234567890")
        self.assertTrue(url.startswith("https://bandcamp.com/EmbeddedPlayer/album=1234567890/"))
        self.assertTrue(bandcamp_player_url("track", "7").startswith("https://bandcamp.com/EmbeddedPlayer/track=7/"))

    def test_nothing_but_a_known_kind_and_digits_reach_the_address(self):
        self.assertEqual(bandcamp_player_url("album", '12ab"><script>'), "")
        self.assertEqual(bandcamp_player_url("playlist", "12"), "")
        self.assertEqual(bandcamp_player_url("album", ""), "")
        self.assertEqual(bandcamp_player_url("album", "١٢٣"), "")


class BandcampPlayerFieldsTestCase(TestCase):
    def test_an_id_that_is_not_a_number(self):
        band = Band(name="Krill", bandcamp_embed_kind="album", bandcamp_embed_id='12ab"><script>')
        with self.assertRaises(ValidationError) as caught:
            band.full_clean()
        self.assertIn("bandcamp_embed_id", caught.exception.message_dict)
        band.bandcamp_embed_id = "1234567890"
        band.full_clean()

    def test_the_url_a_player_was_read_from(self):
        band = found()
        self.assertTrue(band.bandcamp_player_usable)
        self.assertEqual(band.bandcamp_embed_for, band.bandcamp_url)
        self.assertEqual(band.bandcamp_player_url, bandcamp_player_url("album", "1234567890"))

    def test_stale_player_is_not_usable(self):
        band = found()
        band.bandcamp_url = "https://krill-new.bandcamp.com/"
        self.assertFalse(band.bandcamp_player_usable)
        # an editor's player is exempt
        band.field_sources = {"bandcamp_embed": "editor"}
        self.assertTrue(band.bandcamp_player_usable)

    def test_an_editors_player_is_usable_whatever_the_status(self):
        artist = Artist(
            name="A", bandcamp_embed_kind="track", bandcamp_embed_id="9", field_sources={"bandcamp_embed": "editor"}
        )
        self.assertTrue(artist.bandcamp_player_usable)

    def test_not_usable_without_kind_and_id_or_when_not_found(self):
        self.assertFalse(found(name="A", bandcamp_embed_id="").bandcamp_player_usable)
        self.assertFalse(found(name="B", bandcamp_embed_kind="").bandcamp_player_usable)
        self.assertFalse(found(name="C", bandcamp_embed_status="no_playable").bandcamp_player_usable)
        self.assertFalse(found(name="D", bandcamp_embed_status="declined").bandcamp_player_usable)
