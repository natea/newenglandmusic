from django.test import TestCase

from core.models import Artist, Band

KRILL = "https://krill.bandcamp.com/"


def found(model=Band, name="Krill", **fields):
    values = dict(
        name=name, bandcamp_url=KRILL, bandcamp_embed_kind="album", bandcamp_embed_id="111", bandcamp_embed_status="found",
        bandcamp_embed_for=KRILL,
    )
    return model.objects.create(**{**values, **fields})


class BandcampBandPageTestCase(TestCase):
    def html(self, act):
        response = self.client.get(act.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_band_page_with_a_player(self):
        for model in (Band, Artist):
            with self.subTest(model=model):
                html = self.html(found(model, name=f"Act {model.__name__}"))
                self.assertIn("Listen on Bandcamp", html)
                self.assertIn("▶ Play Act", html)
                self.assertIn('data-bandcamp-id="111"', html)
                # nothing from bandcamp until play is pressed
                self.assertNotIn("<iframe", html)
                self.assertNotIn("EmbeddedPlayer", html)
                self.assertNotIn("<img", html.split("Listen on Bandcamp")[1].split("</section>")[0])

    def test_the_section_comes_after_the_links(self):
        html = self.html(found(website="https://krill.example"))
        self.assertLess(html.index('class="act-links"'), html.index("Listen on Bandcamp"))

    def test_band_page_with_no_player(self):
        band = found(bandcamp_embed_status="no_playable", bandcamp_embed_kind="", bandcamp_embed_id="")
        html = self.html(band)
        self.assertNotIn("Listen on Bandcamp", html)
        self.assertIn(">Bandcamp<", html)
        self.assertIn(f'href="{KRILL}"', html)

    def test_no_section_for_a_stale_declined_or_held_player(self):
        stale = found(name="Stale", bandcamp_embed_for="https://old.bandcamp.com/")
        declined = found(name="Declined", bandcamp_embed_status="declined", bandcamp_embed_kind="", bandcamp_embed_id="")
        for act in (stale, declined):
            with self.subTest(act=act.name):
                self.assertNotIn("Listen on Bandcamp", self.html(act))

    def test_an_editors_player_shows_even_with_a_changed_address(self):
        band = found(bandcamp_embed_for="https://old.bandcamp.com/", field_sources={"bandcamp_embed": "editor"})
        self.assertIn("Listen on Bandcamp", self.html(band))

    def test_band_page_without_javascript(self):
        # the play button is a link to the act's Bandcamp page
        html = self.html(found())
        button = html[html.index('<a class="bandcamp-play"'):]
        self.assertTrue(button.startswith(f'<a class="bandcamp-play" href="{KRILL}"'))
        self.assertIn('target="_blank"', button.split(">")[0])
