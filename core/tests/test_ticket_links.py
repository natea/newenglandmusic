from pathlib import Path

from core.event_fetching.ticket_links import find_ticket_links, match_show, slugify
from django.test import SimpleTestCase

# the links on toad's place's and the sinclair's pages, recorded 2026-10-29
FIXTURES = Path(__file__).parent / "fixtures" / "ticket_links"


def links(name):
    return find_ticket_links((FIXTURES / name).read_text())


class FindTicketLinksTestCase(SimpleTestCase):
    def test_etix_show_and_venue_links(self):
        shows, venues = links("toads_place.html")
        self.assertEqual(venues, ["https://www.etix.com/ticket/v/677"])
        self.assertEqual(len(shows), 30)
        self.assertEqual(
            shows["https://www.etix.com/ticket/p/96934398/as-i-lay-dying-new-haven-toads-place-of-new-haven"],
            "as-i-lay-dying-new-haven-toads-place-of-new-haven",
        )

    def test_axs_show_and_venue_links(self):
        shows, venues = links("the_sinclair.html")
        self.assertEqual(venues, ["https://www.axs.com/venues/124878/the-sinclair-cambridge-tickets"])
        self.assertEqual(len(shows), 20)
        self.assertIn("https://www.axs.com/events/1329972/hiss-golden-messenger-tickets", shows)

    def test_query_strings_and_other_links_are_ignored(self):
        shows, venues = find_ticket_links(
            '<a href="https://www.etix.com/ticket/p/1/a-show-town?partner_id=9">x</a>'
            '<a href="https://www.etix.com/ticket/p/1/a-show-town#buy">x</a>'
            '<a href="https://www.etix.com/help">x</a>'
            '<a href="https://seatgeek.com/venues/x">x</a>'
        )
        self.assertEqual(shows, {"https://www.etix.com/ticket/p/1/a-show-town": "a-show-town"})
        self.assertEqual(venues, [])

    def test_no_links(self):
        self.assertEqual(find_ticket_links("<p>no shows</p>"), ({}, []))


class MatchShowTestCase(SimpleTestCase):
    def setUp(self):
        self.toads, _ = links("toads_place.html")
        self.sinclair, _ = links("the_sinclair.html")

    def test_shows_own_page_found(self):
        self.assertEqual(
            match_show(self.toads, "As I Lay Dying"),
            "https://www.etix.com/ticket/p/96934398/as-i-lay-dying-new-haven-toads-place-of-new-haven",
        )
        self.assertEqual(
            match_show(self.sinclair, "Hiss Golden Messenger"),
            "https://www.axs.com/events/1329972/hiss-golden-messenger-tickets",
        )

    def test_title_run_into_the_tour_name(self):
        # etix drops the colon: "eggythe-final-tour-of-2026", "wheeler-walker-jrpullinout..."
        self.assertIn("/eggythe-final-tour-of-2026-", match_show(self.toads, "Eggy"))
        self.assertIn("/wheeler-walker-jrpullinout", match_show(self.toads, "Wheeler Walker Jr."))

    def test_headliner_when_the_title_doesnt_match(self):
        url = match_show(self.toads, "From Ashes To New with Nevertel, Hollow Pact", "From Ashes To New")
        self.assertIn("/from-ashes-to-new-reflections-tour-2027-", url)

    def test_recurring_title(self):
        # three different saturday night dance parties
        self.assertEqual(match_show(self.toads, "Saturday Night Dance Party"), "")

    def test_no_match(self):
        self.assertEqual(match_show(self.toads, "Some Other Band"), "")
        # etix censors the name, so this falls back to the venue's list
        self.assertEqual(match_show(self.toads, "Alaska Thunderfuck"), "")

    def test_short_titles_are_not_matched(self):
        self.assertEqual(match_show({"https://www.etix.com/ticket/p/1/xo-tour": "xo-tour"}, "XO"), "")


class SlugifyTestCase(SimpleTestCase):
    def test_like_etix(self):
        self.assertEqual(slugify("Toad's Place"), "toads-place")
        self.assertEqual(slugify("Adult."), "adult")
        self.assertEqual(slugify("Beyoncé & Jay-Z"), "beyonce-jay-z")
