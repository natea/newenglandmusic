from datetime import timedelta

from core.models import Artist, Band, Event, EventPerformer, Venue
from core.views.act_index import letter_of, sort_name
from django.test import SimpleTestCase, TestCase
from django.utils import timezone


class FilingTestCase(SimpleTestCase):
    def test_sort_name_and_letter(self):
        self.assertEqual(sort_name("The Atlantics"), "Atlantics")
        self.assertEqual([letter_of(n) for n in ("The Atlantics", "28 Degrees Taurus", "Élan", "'Til Tuesday", "Belly")], ["A", "#", "E", "#", "B"])


class ActIndexTestCase(TestCase):
    def setUp(self):
        self.belly = Band.objects.create(name="Belly", city_town="Providence", state="RI")
        self.anjimile = Artist.objects.create(name="Anjimile", city_town="Boston", state="MA")

    def page(self):
        response = self.client.get("/bands")
        self.assertEqual(response.status_code, 200)
        return response

    def entries(self, response):
        return {letter: [act.name for _, _, acts in pages for act in acts] for letter, pages in response.context["groups"]}

    def test_bands_and_artists_together(self):
        response = self.page()
        self.assertEqual(self.entries(response), {"A": ["Anjimile"], "B": ["Belly"]})
        self.assertContains(response, '<a class="index-name" href="/bands/belly">Belly</a>', html=True)
        self.assertContains(response, '<a class="index-name" href="/artists/anjimile">Anjimile</a>', html=True)
        self.assertContains(response, "<span>band</span><span>,&nbsp;Providence, RI</span>")
        self.assertContains(response, "<span>artist</span><span>,&nbsp;Boston, MA</span>")

    def test_the_names_inverted_in_the_index_only(self):
        band = Band.objects.create(name="The Atlantics")
        response = self.page()
        self.assertContains(response, f'<a class="index-name" href="{band.get_absolute_url()}">Atlantics, The</a>', html=True)
        # the act's own page and search keep its name
        self.assertContains(self.client.get(band.get_absolute_url()), "The Atlantics")
        self.assertContains(self.client.get("/", {"s": "atlantics"}), ">The <mark>Atlantics</mark></a>")

    def test_a_leading_the_and_digits(self):
        Band.objects.create(name="The Atlantics")
        Band.objects.create(name="28 Degrees Taurus")
        entries = self.entries(self.page())
        self.assertEqual(entries["#"], ["28 Degrees Taurus"])
        self.assertEqual(entries["A"], ["Anjimile", "The Atlantics"])
        # "#" comes first in the rail and the page
        self.assertEqual(list(entries)[0], "#")

    def test_the_next_show(self):
        venue = Venue.objects.create(sheet_id="V0001", name="Paradise", state="MA")
        when = timezone.now() + timedelta(days=14)
        event = Event.all_objects.create(title="", artists="Belly", starttime=when, venue=venue, is_approved=True)
        EventPerformer.objects.create(event=event, band=self.belly, order=0)
        response = self.page()
        acts = {act.name: act for _, pages in response.context["groups"] for _, _, page in pages for act in page}
        self.assertEqual(acts["Belly"].next_show, when)
        self.assertIsNone(acts["Anjimile"].next_show)
        self.assertContains(response, f'<time class="index-next" datetime="{timezone.localtime(when).isoformat()}">', count=1)

    def test_a_show_next_year_carries_its_year(self):
        venue = Venue.objects.create(sheet_id="V0001", name="Paradise", state="MA")
        when = timezone.now() + timedelta(days=400)
        event = Event.all_objects.create(title="", artists="Belly", starttime=when, venue=venue, is_approved=True)
        EventPerformer.objects.create(event=event, band=self.belly, order=0)
        local = timezone.localtime(when)
        self.assertContains(self.page(), f"{local:%b} {local.day}, {local.year}</time>")

    def test_an_unapproved_show_isnt_a_next_show(self):
        venue = Venue.objects.create(sheet_id="V0001", name="Paradise", state="MA")
        event = Event.all_objects.create(title="", artists="Belly", starttime=timezone.now() + timedelta(days=3), venue=venue, is_approved=False)
        EventPerformer.objects.create(event=event, band=self.belly, order=0)
        acts = {act.name: act for _, pages in self.page().context["groups"] for _, _, page in pages for act in page}
        self.assertIsNone(acts["Belly"].next_show)

    def test_held_acts_left_out(self):
        Band.objects.create(name="3 1/2 Girls", needs_review=True, review_reasons=["not_found"])
        response = self.page()
        self.assertNotIn("#", self.entries(response))
        self.assertNotContains(response, "3 1/2 Girls")

    def test_pages_and_guide_words(self):
        from core.views.act_index import PAGE_SIZE

        for n in range(PAGE_SIZE + 1):
            Band.objects.create(name=f"Bellwether {n:02d}")
        pages = dict(self.page().context["groups"])["B"]
        self.assertEqual([len(acts) for _, _, acts in pages], [PAGE_SIZE, 2])
        self.assertEqual(pages[0][:2], ("Bellwether 00", "Bellwether 39"))
        # a page of one name has one guide word
        self.assertEqual(pages[1][:2], ("Bellwether 40", "Belly"))

    def test_countries_shortened(self):
        Artist.objects.create(name="Béla Fleck", area="United States")
        self.assertContains(self.page(), "<span>artist</span><span>,&nbsp;US</span>")

    def test_the_artists_address(self):
        response = self.client.get("/artists")
        self.assertEqual((response.status_code, response["Location"]), (301, "/bands"))

    def test_a_trailing_slash(self):
        for typed, page in (("/bands/", "/bands"), ("/artists/", "/artists"), ("/bands/belly/", "/bands/belly"),
                            ("/artists/anjimile/?ref=x", "/artists/anjimile?ref=x")):
            response = self.client.get(typed)
            self.assertEqual((response.status_code, response["Location"]), (301, page), typed)
        # and on to the index, from /artists
        self.assertRedirects(self.client.get("/bands/", follow=True), "/bands", status_code=301)

    def test_the_rail_links_only_letters_with_acts(self):
        response = self.page()
        self.assertContains(response, '<a href="#letter-A">A</a>', html=True)
        self.assertContains(response, '<span aria-hidden="true">Q</span>', html=True)


class MenuItemTestCase(TestCase):
    def test_the_menu_links_to_the_index(self):
        from core.models import MenuItem

        item = MenuItem.objects.get(url="/bands")
        self.assertEqual((item.name, item.show_in_header), ("Bands & artists", True))
        self.assertContains(self.client.get("/bands"), 'href="/bands"')
