"""how an event's row reads in a listing (add-event-pages, event-listing)"""

from django.test import TestCase
from django.utils import timezone

from core.event_performers import link_from_names
from core.models import Band, Event, Venue


class ListingRowTestCase(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(sheet_id="V1", name="Paradise", city_town="Boston", state="MA")

    def row(self, **fields):
        fields.setdefault("starttime", timezone.now() + timezone.timedelta(days=3))
        event = Event.all_objects.create(venue=self.venue, **fields)
        link_from_names(event)
        event = Event.all_objects.get(pk=event.pk)
        return event, event.baked_html_template

    def test_one_link_to_the_event_page(self):
        Band.objects.create(name="Disko Lunatics")
        event, html = self.row(title="Disko Lunatics", artists="Miss Chief", hyperlink="https://paradise.example/show")
        self.assertIn(f'<a class="event-headline" href="/event/{event.pk}"><b class="event-headliner">Disko Lunatics</b></a>', html)
        self.assertNotIn('href="/bands/', html)
        self.assertNotIn("info ↗", html)
        self.assertNotIn('target="_blank"', html.split('class="event-ticket"')[0])

    def test_an_event_with_no_performers(self):
        event, html = self.row(title="Some Night", artists="Nobody", hyperlink="https://paradise.example/show")
        self.assertIn(f'<a class="event-headline" href="/event/{event.pk}">', html)
        self.assertNotIn('href="https://paradise.example/show"', html)

    def test_a_headliner_and_openers(self):
        _, html = self.row(title="Disko Lunatics", artists="Miss Chief, Trading Tombstones")
        self.assertIn('<b class="event-headliner">Disko Lunatics</b></a><span class="event-openers"> with Miss Chief, Trading Tombstones</span>', html)

    def test_no_act_in_the_title(self):
        _, html = self.row(title="Bluegrass Jam", artists="Frank Drake")
        self.assertIn('<b class="event-headliner">Frank Drake</b>', html)
        _, html = self.row(title="Bluegrass Jam")
        self.assertIn('<b class="event-headliner">Bluegrass Jam</b>', html)

    def test_a_title_that_adds_something(self):
        _, html = self.row(title="Halloween Show", artists="Disko Lunatics, Miss Chief")
        self.assertIn('<span class="event-title-line">Halloween Show</span><a class="event-headline"', html)

    def test_a_title_that_is_only_the_names(self):
        _, html = self.row(title="Dev Lemons, Venus & the Flytraps", artists="Dev Lemons, Venus & the Flytraps")
        self.assertNotIn("event-title-line", html)
        visible = html.split('class="event-content"')[1]
        self.assertEqual(visible.count("Venus &amp; the Flytraps"), 1)
        self.assertIn("with Venus &amp; the Flytraps", html)

    def test_the_headliner_in_both(self):
        _, html = self.row(title="Kim Deal", artists="Kim Deal, Pile")
        self.assertIn('<b class="event-headliner">Kim Deal</b></a><span class="event-openers"> with Pile</span>', html)

    def test_ticket_badge(self):
        _, html = self.row(title="Zipper", ticket_hyperlink="https://tix.example/9")
        self.assertIn('<a href="https://tix.example/9" target="_blank" class=\'ticket\'>tix</a>', html)

    def test_map_attributes_kept(self):
        event, html = self.row(title="Zipper", artists="Pile")
        self.assertIn(f'id="event-{event.pk}"', html)
        self.assertIn('data-title-and-artists="Zipper: Pile"', html)
        self.assertIn(f'data-venue-id="{self.venue.pk}"', html)
