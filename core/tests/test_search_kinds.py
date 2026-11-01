from datetime import timedelta

from core.models import Artist, Band, Event, EventPerformer, Venue
from django.test import TestCase
from django.utils import timezone


class SearchResultsTestCase(TestCase):
    def setUp(self):
        self.belly = Band.objects.create(name="Belly", city_town="Providence", state="RI")
        self.obriens = Venue.objects.create(sheet_id="V0001", name="O'Brien's Pub", city_town="Allston", state="MA")

    def search(self, words):
        response = self.client.get("/", {"s": words})
        self.assertEqual(response.status_code, 200)
        return response

    def groups(self, response):
        return [group for group, _ in response.context["groups"]]

    def test_a_band_by_name(self):
        Event.all_objects.create(title="", artists="Belly", starttime=timezone.now() + timedelta(days=5), venue=self.obriens, is_approved=True)
        response = self.search("belly")
        self.assertEqual(self.groups(response), ["Bands & artists"])
        self.assertContains(response, '<a class="index-name" href="/bands/belly"><mark>Belly</mark></a>', html=True)
        self.assertContains(response, "<span>band</span><span>,&nbsp;Providence, RI</span>")
        html = response.content.decode()
        self.assertLess(html.index('<h2 class="search-head">Bands &amp; artists'), html.index('<h2 class="search-head">Shows'))

    def test_a_venue_by_name(self):
        response = self.search("o'brien")
        self.assertEqual(self.groups(response), ["Venues"])
        self.assertContains(response, "<a class=\"index-name\" href=\"/?s=O%27Brien%27s+Pub\"><mark>O&#x27;Brien</mark>&#x27;s Pub</a>", html=True)
        self.assertContains(response, "Allston, MA")
        # punctuation and case ignored either way round
        self.assertEqual(self.groups(self.search("OBRIENS")), ["Venues"])

    def test_no_act_matches(self):
        Event.all_objects.create(title="Karaoke night", artists="", starttime=timezone.now() + timedelta(days=5), venue=self.obriens, is_approved=True)
        response = self.search("karaoke")
        self.assertEqual(self.groups(response), [])
        self.assertContains(response, '<h2 class="search-head">Shows')
        self.assertNotContains(response, '<h2 class="search-head">Bands')

    def test_accents_ignored(self):
        Artist.objects.create(name="Élan Vital")
        self.assertContains(self.search("elan"), "<mark>Élan</mark> Vital")

    def test_held_acts_and_inactive_venues_left_out(self):
        Band.objects.create(name="Bellyache", needs_review=True, review_reasons=["not_found"])
        Venue.objects.create(sheet_id="V0002", name="Belly Up Tavern", is_active=False)
        response = self.search("belly")
        self.assertNotContains(response, "Bellyache")
        self.assertNotContains(response, "Belly Up Tavern")

    def test_without_javascript(self):
        # the search box is a plain get form: the script only enhances it
        home = self.client.get("/").content.decode()
        # empty, not a missing variable's placeholder, on a page that isn't a search
        self.assertIn("name='s' value=''", home)
        self.assertIn("<form class='site-search' method='GET' action='/' role='search'>", home)
        self.assertIn("<input type='search' name='s'", home)
        self.assertContains(self.search("belly"), '<a class="index-name" href="/bands/belly"><mark>Belly</mark></a>', html=True)

    def test_one_box_showing_what_was_searched(self):
        html = self.search("belly").content.decode()
        self.assertEqual(html.count("name='s'") + html.count('name="s"'), 1)
        self.assertIn("name='s' value='belly'", html)
        # and none in the menu
        menu = html[html.index("id='burgerMenuContents'"):]
        self.assertNotIn("name='s'", menu[:menu.index("</div>")])

    def test_what_was_searched_is_marked(self):
        response = self.search("bel")
        self.assertContains(response, '<a class="index-name" href="/bands/belly"><mark>Bel</mark>ly</a>', html=True)

    def test_nothing_found(self):
        response = self.search("zzzz")
        self.assertContains(response, "Nothing found for “zzzz”")
        self.assertNotContains(response, 'class="search-head"')


class ShowRowsTestCase(TestCase):
    def test_upcoming_soonest_first_then_past_newest_first(self):
        venue = Venue.objects.create(sheet_id="V0001", name="Paradise Rock Club", city_town="Boston", state="MA")
        for days, title in ((9, "later"), (2, "sooner"), (-3, "recent"), (-30, "older")):
            Event.all_objects.create(title=f"belly {title}", artists="", starttime=timezone.now() + timedelta(days=days), venue=venue, is_approved=True)
        response = self.client.get("/", {"s": "belly"})
        self.assertEqual([e.title for e in response.context["upcoming_shows"]], ["belly sooner", "belly later"])
        self.assertEqual([e.title for e in response.context["past_shows"]], ["belly recent", "belly older"])
        html = response.content.decode()
        self.assertIn("Paradise Rock Club, Boston, MA", html)
        # compact rows: the calendar's stored listing isn't used, and a show with no venue says nothing
        self.assertNotIn('class="show-where">None', html)
        self.assertNotIn('class="event-time-and-content"', html)

    def test_an_acts_next_show(self):
        band = Band.objects.create(name="Belly")
        venue = Venue.objects.create(sheet_id="V0001", name="Paradise Rock Club")
        when = timezone.now() + timedelta(days=4)
        event = Event.all_objects.create(title="", artists="Belly", starttime=when, venue=venue, is_approved=True)
        EventPerformer.objects.create(event=event, band=band, order=0)
        local = timezone.localtime(when)
        self.assertContains(self.client.get("/", {"s": "belly"}), f'<time class="index-next" datetime="{local.isoformat()}">')


class SuggestTestCase(TestCase):
    def setUp(self):
        Band.objects.create(name="Belly", city_town="Providence", state="RI")
        Artist.objects.create(name="Belly", area="Toronto")
        self.paradise = Venue.objects.create(sheet_id="V0001", name="Paradise Rock Club", city_town="Boston", state="MA")
        when = timezone.now() + timedelta(days=9)
        self.show = Event.all_objects.create(title="", artists="Belly", starttime=when, venue=self.paradise, is_approved=True)
        Event.all_objects.create(title="", artists="Belly", starttime=when, venue=self.paradise, is_approved=False)
        Event.all_objects.create(title="", artists="Belly", starttime=timezone.now() - timedelta(days=9), venue=self.paradise, is_approved=True)

    def suggest(self, q):
        response = self.client.get("/search/suggest", {"q": q})
        self.assertEqual(response.status_code, 200)
        return response.json()["items"]

    def test_suggestions_by_kind(self):
        items = self.suggest("bel")
        self.assertEqual(
            [(item["group"], item["kind"], item["name"]) for item in items],
            [("Bands & artists", "band", "Belly"), ("Bands & artists", "artist", "Belly"), ("Shows", "show", "Belly")],
        )
        band, artist, show = items
        self.assertEqual((band["url"], band["detail"]), ("/bands/belly", "Providence, RI"))
        self.assertEqual(artist["detail"], "Toronto")
        # upcoming approved shows only, with their date and venue
        start = timezone.localtime(self.show.starttime)
        self.assertEqual((show["url"], show["detail"]), (f"/event/{self.show.pk}", f"{start:%b} {start.day} · Paradise Rock Club"))

    def test_a_venue_and_a_show_there(self):
        Event.all_objects.create(title="Paradise anniversary", artists="", starttime=timezone.now() + timedelta(days=3), venue=self.paradise, is_approved=True)
        kinds = [(item["kind"], item["name"]) for item in self.suggest("paradise")]
        self.assertEqual(kinds, [("venue", "Paradise Rock Club"), ("show", "Paradise anniversary")])

    def test_five_per_kind(self):
        for n in range(7):
            Band.objects.create(name=f"Bellwether {n}")
        bands = [item for item in self.suggest("bell") if item["kind"] == "band"]
        self.assertEqual(len(bands), 5)

    def test_too_short(self):
        self.assertEqual(self.suggest("b"), [])
        self.assertEqual(self.suggest(" b "), [])


class RankingTestCase(TestCase):
    def test_names_starting_with_the_words_first(self):
        from core.search_kinds import acts, venues

        for name in ("Dan Campbell", "Belen", "Bellcave"):
            Artist.objects.create(name=name)
        Venue.objects.create(sheet_id="V0001", name="Campbell Hall")
        Venue.objects.create(sheet_id="V0002", name="Bell in Hand")
        self.assertEqual([m.name for m in acts("bel", 5)], ["Belen", "Bellcave", "Dan Campbell"])
        self.assertEqual([m.name for m in venues("bel", 5)], ["Bell in Hand", "Campbell Hall"])
