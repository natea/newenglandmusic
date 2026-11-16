"""an event's own page at /event/<id> (add-event-pages, event-pages)"""

from django.test import TestCase, override_settings
from django.utils import timezone

from core.event_performers import link_from_names
from core.models import Band, Event, EventPerformer, Venue
from core.views.event_page import outbound_links, same_link


def days(n, hour=20):
    return timezone.localtime(timezone.now() + timezone.timedelta(days=n)).replace(hour=hour, minute=0, second=0, microsecond=0)


@override_settings(SITE_URL="https://stagehopper.app")
class EventPageTestCase(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(
            sheet_id="V1", name="AS220", city_town="Providence", state="RI", neighborhood="Downcity",
            accessibility_notes="Step-free entrance",
        )

    def event(self, **fields):
        fields.setdefault("starttime", days(3))
        fields.setdefault("venue", self.venue)
        return Event.all_objects.create(**fields)

    def page(self, event, **headers):
        return self.client.get(f"/event/{event.pk}", **headers)


class WhichEventsHaveAPageTestCase(EventPageTestCase):
    def test_an_approved_event(self):
        response = self.page(self.event(title="Zipper"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/event_page.html")

    def test_an_event_with_no_performers(self):
        html = self.page(self.event(title="Some Night", artists="Nobody Here, Somebody Else")).content.decode()
        self.assertIn("Nobody Here", html)
        self.assertNotIn('href="/bands/', html)

    def test_unapproved_or_unknown(self):
        self.assertEqual(self.page(self.event(title="Hidden", is_approved=False)).status_code, 404)
        self.assertEqual(self.client.get("/event/999999").status_code, 404)

    def test_a_past_event(self):
        response = self.page(self.event(title="Zipper", starttime=days(-3)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This show has passed.")

    def test_tonights_show_isnt_past(self):
        self.assertNotContains(self.page(self.event(title="Zipper", starttime=timezone.now() - timezone.timedelta(minutes=5))), "has passed")

    def test_no_user_agent(self):
        # some clients send no user agent at all; that was once a server error
        self.assertEqual(self.page(self.event(title="Zipper")).status_code, 200)


class WhatThePageShowsTestCase(EventPageTestCase):
    def test_a_full_event(self):
        event = self.event(
            title="Halloween Show", artists="Disko Lunatics, Miss Chief", price="$15", age_policy_override="21+",
            description="Costumes encouraged.", starttime=days(3, hour=19),
        )
        html = self.page(event).content.decode()
        when = timezone.localtime(event.starttime)
        self.assertIn(f"{when:%a %b} {when.day} · 7:00 p.m.", html)
        self.assertIn('<p class="event-page-title-line">Halloween Show</p>', html)
        self.assertIn(">Disko Lunatics</h1>", html)
        self.assertIn("with Miss Chief", html)
        self.assertIn('<b><a href="/venues/as220">AS220</a></b>, Providence (Downcity), RI', html)
        self.assertIn("Step-free entrance", html)
        self.assertIn("<dd>$15</dd>", html)
        self.assertIn("<dd>21+</dd>", html)
        self.assertIn("Costumes encouraged.", html)
        self.assertIn('class="event-actions"', html)

    def test_play_buttons(self):
        from unittest import mock

        preview = [{"label": "Zipper", "spotify": "abc", "apple": None, "youtube": None, "bandcamp": {"link": "https://zipper.bandcamp.com/", "kind": "album", "id": "1", "page": "https://zipper.bandcamp.com/"}}]
        with mock.patch("core.views.event_page.event_artist_previews", return_value=preview):
            html = self.page(self.event(title="Zipper")).content.decode()
        self.assertIn('class="spotify-play"', html)
        self.assertIn('class="bandcamp-play"', html)

    def test_nothing_drawn_empty(self):
        html = self.page(self.event(title="Zipper")).content.decode()
        for label in ("<dt>Price</dt>", "<dt>Ages</dt>", "event-page-title-line", "event-page-links", "event-page-description", "artist-previews"):
            self.assertNotIn(label, html)

    def test_a_cancelled_event(self):
        self.assertContains(self.page(self.event(title="Zipper", is_cancelled=True)), "This show is cancelled.")


class ActsLinkToTheirPagesTestCase(EventPageTestCase):
    def setUp(self):
        super().setUp()
        for name in ("Axe Collector", "Phantom Rider", "Built To Spill", "Pixies"):
            Band.objects.create(name=name)

    def linked(self, **fields):
        event = self.event(**fields)
        link_from_names(event)
        return self.page(event).content.decode()

    def test_performers_and_a_plain_name(self):
        html = self.linked(title="Axe Collector", artists="Phantom Rider, Anthropocene")
        self.assertIn('<h1 id="event-headliner" class="event-page-headliner"><a href="/bands/axe-collector">Axe Collector</a></h1>', html)
        self.assertIn('with <a href="/bands/phantom-rider">Phantom Rider</a>, Anthropocene</p>', html)

    def test_a_linked_performer_in_the_artists(self):
        html = self.linked(title="show night", artists="Pixies, Dana and Alden")
        self.assertIn('<a href="/bands/pixies">Pixies</a>', html)
        self.assertIn("Dana and Alden", html)
        self.assertNotIn('href="/bands/dana', html)

    def test_a_name_at_the_start_of_a_longer_title(self):
        html = self.linked(title="Built to Spill 3rd Annual Benefit Concert")
        self.assertIn('<a href="/bands/built-to-spill">Built to Spill</a> 3rd Annual Benefit Concert', html)

    def test_a_presenters_prefix_stays_plain(self):
        html = self.linked(title="AS220 Presents: Pixies")
        self.assertIn('<a href="/bands/pixies">Pixies</a></h1>', html)
        self.assertNotIn('href="/bands/as220', html)

    def test_a_performer_awaiting_review(self):
        held = Band.objects.create(name="Glass Halo", needs_review=True, review_reasons=["not_found"])
        event = self.event(title="Glass Halo")
        EventPerformer.objects.create(event=event, band=held, order=0, source=EventPerformer.Source.EDITOR)
        html = self.page(event).content.decode()
        self.assertIn('class="event-page-headliner">Glass Halo</h1>', html)


class OutboundLinksTestCase(EventPageTestCase):
    def test_two_different_links(self):
        html = self.page(self.event(title="Zipper", ticket_hyperlink="https://tix.example/1", hyperlink="https://as220.org/zipper")).content.decode()
        self.assertIn('<a href="https://tix.example/1" target="_blank" rel="noopener">Tickets', html)
        self.assertIn('<a href="https://as220.org/zipper" target="_blank" rel="noopener">Venue&#x27;s page', html)

    def test_the_same_link_twice(self):
        html = self.page(self.event(title="Zipper", ticket_hyperlink="https://as220.org/zipper", hyperlink="https://AS220.org/zipper/?utm_source=x")).content.decode()
        self.assertIn(">Tickets<", html)
        self.assertNotIn("Venue&#x27;s page", html)

    def test_no_ticket_link(self):
        html = self.page(self.event(title="Zipper", hyperlink="https://as220.org/zipper")).content.decode()
        self.assertIn("Venue&#x27;s page", html)
        self.assertNotIn(">Tickets<", html)

    def test_the_comparison(self):
        self.assertTrue(same_link(" https://Example.org/a/ ", "https://example.org/a?utm_medium=email"))
        self.assertFalse(same_link("https://example.org/a", "https://example.org/b"))
        self.assertEqual(outbound_links(Event(ticket_hyperlink="", hyperlink="")), [])


class SharingAndSearchTestCase(EventPageTestCase):
    def test_share_preview(self):
        event = self.event(title="Zipper", artists="Anthropocene", starttime=days(3, hour=19))
        html = self.page(event).content.decode()
        when = timezone.localtime(event.starttime)
        self.assertIn(f'content="{when.month}/{when.day} 7pm @ AS220 - Zipper: Anthropocene"', html)
        self.assertIn('property="og:description"', html)
        self.assertNotIn('http-equiv="refresh"', html)

    def test_an_upcoming_event_can_be_indexed(self):
        event = self.event(title="Zipper")
        html = self.page(event).content.decode()
        self.assertNotIn("noindex", html)
        self.assertIn(f'<link rel="canonical" href="https://stagehopper.app/event/{event.pk}">', html)

    def test_a_past_event_isnt_indexed(self):
        html = self.page(self.event(title="Zipper", starttime=days(-2))).content.decode()
        self.assertIn('<meta name="robots" content="noindex">', html)
        self.assertNotIn('rel="canonical"', html)

    def test_the_weekly_email_and_search_link_here(self):
        from django.urls import reverse

        event = self.event(title="Zipper")
        self.assertEqual(reverse("event_page", args=[event.pk]), f"/event/{event.pk}")
        self.assertEqual(self.client.get(reverse("event_page", args=[event.pk])).status_code, 200)
