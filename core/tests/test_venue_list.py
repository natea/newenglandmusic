"""the venue list at /venues and each venue's artist view (add-venue-list)"""

from django.test import TestCase, override_settings

from core.geo_filters import COOKIE_NAME
from core.models import MenuItem, Venue
from core.tests.geo_fixture import load_geo_fixture


def venue(name, town="Boston", state="MA", **fields):
    return Venue.objects.create(name=name, city_town=town, state=state, sheet_id=name[:30], **fields)


class VenueListTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()

    def names(self, response):
        return [v.name for _, entries in response.context["groups"] for v in entries]

    def get(self, url, **kwargs):
        response = self.client.get(url, **kwargs)
        self.assertEqual(response.status_code, 200, url)
        return response


class TheListTestCase(VenueListTestCase):
    def test_alphabetical_list(self):
        for name in ("The Sinclair", "Brighton Music Hall", "O'Brien's"):
            venue(name)
        response = self.get("/venues")
        self.assertEqual(self.names(response), ["Brighton Music Hall", "O'Brien's", "The Sinclair"])
        self.assertContains(response, 'href="/venues/obriens"')

    def test_menu_link(self):
        self.assertTrue(MenuItem.objects.filter(url="/venues", name="Venues").exists())
        self.assertContains(self.get("/bands"), 'href="/venues"')

    def test_inactive_venue(self):
        venue("Closed Club", is_active=False)
        venue("Maybe Club")
        self.assertEqual(self.names(self.get("/venues")), ["Maybe Club"])

    def test_outside_new_england(self):
        venue("Bowery Ballroom", town="New York", state="NY")
        self.assertEqual(self.names(self.get("/venues")), [])

    def test_a_sparse_venue(self):
        venue("The Shed", town="Brattleboro", state="VT")
        html = self.get("/venues").content.decode()
        self.assertIn('<span class="venue-entry-detail">Brattleboro, VT</span>', html)

    def test_a_full_entry(self):
        venue("O'Brien's", neighborhood="Allston", venue_type="Bar", size=Venue.Size.SMALL, genres=["Rock", "Punk"])
        self.assertContains(self.get("/venues"), '<span class="venue-entry-detail">Boston (Allston), MA · Bar · Small · Rock, Punk</span>')

    def test_trailing_slash(self):
        self.assertRedirects(self.client.get("/venues/"), "/venues", status_code=301, fetch_redirect_response=False)

    def test_can_be_indexed(self):
        with override_settings(SITE_URL="https://stagehopper.app"):
            html = self.get("/venues?state=vermont").content.decode()
        self.assertNotIn("noindex", html)
        self.assertIn('<link rel="canonical" href="https://stagehopper.app/venues">', html)

    def test_title_and_description(self):
        html = self.get("/venues").content.decode()
        self.assertIn("<title>Venues |", html)
        self.assertIn('name="description" content="Every New England music venue', html)


class PlaceAndGenreTestCase(VenueListTestCase):
    def setUp(self):
        super().setUp()
        venue("Jazz Spot", town="Somerville", genres=["Jazz"])
        venue("Anything Goes", town="Cambridge", genres=["ALL"])
        venue("Funk House", town="Somerville", genres=["Funk"])
        venue("Green Mountain Jazz", town="Burlington", state="VT", genres=["jazz"])

    def test_by_town(self):
        response = self.get("/venues?metro=ma-north-of-the-charles&town=Somerville%2C+MA")
        self.assertEqual(self.names(response), ["Funk House", "Jazz Spot"])

    def test_by_genre(self):
        names = self.names(self.get("/venues?genre=Jazz"))
        self.assertEqual(names, ["Anything Goes", "Green Mountain Jazz", "Jazz Spot"])

    def test_place_and_genre_together(self):
        self.assertEqual(self.names(self.get("/venues?state=massachusetts&genre=Jazz")), ["Anything Goes", "Jazz Spot"])

    def test_genre_case(self):
        response = self.get("/venues?genre=jazz")
        self.assertIn("Green Mountain Jazz", self.names(response))
        self.assertEqual([g.casefold() for g in response.context["genres"]].count("jazz"), 1)
        self.assertNotIn("ALL", response.context["genres"])

    def test_unknown_value(self):
        self.assertEqual(len(self.names(self.get("/venues?genre=No+Such+Genre"))), 4)

    def test_nothing_matches(self):
        response = self.get("/venues?state=vermont&genre=Funk")
        self.assertContains(response, "No venues match")
        self.assertContains(response, 'href="/venues?clear=1">show all</a>')

    def test_nothing_matches_on_genre_alone(self):
        Venue.objects.filter(name="Anything Goes").delete()
        response = self.get("/venues?genre=Funk&open_booking=1")
        self.assertContains(response, "No venues match")
        self.assertContains(response, 'href="/venues?clear=1">show all</a>')

    def test_show_all_keeps_the_other_filters(self):
        html = self.get("/venues?state=vermont&genre=Jazz").content.decode()
        self.assertIn('href="/venues?clear=1&amp;genre=Jazz">show all</a>', html)
        response = self.get("/venues?clear=1&genre=Jazz")
        self.assertEqual(self.names(response), ["Anything Goes", "Green Mountain Jazz", "Jazz Spot"])

    def test_clear_with_a_genre_doesnt_redirect(self):
        self.client.cookies[COOKIE_NAME] = "state=vermont"
        self.assertEqual(self.client.get("/venues?clear=1&genre=Jazz").status_code, 200)

    def test_choosing_all_for_the_place_keeps_the_other_filters(self):
        self.client.cookies[COOKIE_NAME] = "state=vermont"
        response = self.get("/venues?state=&metro=&genre=Jazz")
        self.assertEqual(self.names(response), ["Anything Goes", "Green Mountain Jazz", "Jazz Spot"])
        self.assertEqual(response.cookies[COOKIE_NAME].value, "")

    def test_changing_the_place_keeps_the_other_filters(self):
        html = self.get("/venues?genre=Jazz&open_booking=1").content.decode()
        self.assertIn('<input type="hidden" name="genre" value="Jazz" data-extra>', html)
        self.assertIn('<input type="hidden" name="open_booking" value="1" data-extra>', html)
        self.assertIn(":not([data-extra])", html)


class OpenBookingsTestCase(VenueListTestCase):
    def setUp(self):
        super().setUp()
        venue("Takes Them", town="Burlington", state="VT", open_booking=True, booking_type=Venue.BookingType.SUBMIT_ARTIST)
        venue("Doesnt", town="Burlington", state="VT", open_booking=False)
        venue("Unknown", town="Burlington", state="VT")
        venue("Boston Open", open_booking=True)

    def test_open_bookings_only(self):
        self.assertEqual(self.names(self.get("/venues?open_booking=1")), ["Boston Open", "Takes Them"])

    def test_with_a_place_filter(self):
        self.assertEqual(self.names(self.get("/venues?open_booking=1&state=vermont")), ["Takes Them"])

    def test_entry_links_go_to_the_artist_view(self):
        self.assertContains(self.get("/venues?open_booking=1"), 'href="/venues/takes-them/booking"')

    def test_booking_type_shown(self):
        self.assertContains(self.get("/venues?open_booking=1"), '<span class="venue-entry-booking">Submit an Artist</span>')

    def test_fan_filters_alone(self):
        html = self.get("/venues").content.decode()
        self.assertIn('href="/venues/takes-them"', html)
        self.assertNotIn("/booking", html.split('class="venue-entries"')[1])
        self.assertIn("For artists", html)
        self.assertIn('name="open_booking"', html)


class RememberedPlaceTestCase(VenueListTestCase):
    def test_returning_visitor(self):
        self.client.cookies[COOKIE_NAME] = "state=massachusetts"
        self.assertRedirects(self.client.get("/venues"), "/venues?state=massachusetts", fetch_redirect_response=False)

    def test_shared_link_keeps_its_filters(self):
        self.client.cookies[COOKIE_NAME] = "state=massachusetts"
        venue("Jazz Spot", genres=["Jazz"])
        self.assertRedirects(self.client.get("/venues?open_booking=1&genre=Jazz"), "/venues?state=massachusetts&genre=Jazz&open_booking=1", fetch_redirect_response=False)

    def test_genre_isnt_remembered(self):
        venue("Jazz Spot", genres=["Jazz"])
        venue("Funk House", genres=["Funk"])
        response = self.get("/venues?genre=Jazz")
        self.assertNotIn(COOKIE_NAME, response.cookies)
        self.assertEqual(self.names(self.get("/venues")), ["Funk House", "Jazz Spot"])

    def test_the_list_sets_the_shared_cookie(self):
        response = self.get("/venues?state=vermont")
        self.assertEqual(response.cookies[COOKIE_NAME].value, "state=vermont")
        self.assertRedirects(self.client.get("/"), "/?state=vermont", fetch_redirect_response=False)


class ArtistViewTestCase(VenueListTestCase):
    def setUp(self):
        super().setUp()
        self.obriens = venue(
            "O'Brien's", open_booking=True, booking_url="https://obriens.example/book", booking_notes="Email the booker with links.",
            booking_type=Venue.BookingType.SUBMIT_ARTIST, website="https://obriens.example", open_mic=False, size=Venue.Size.SMALL, genres=["Rock"],
        )

    def view(self, v):
        return self.client.get(f"/venues/{v.slug}/booking")

    def test_switching_views(self):
        html = self.client.get("/venues/obriens").content.decode()
        self.assertIn('<a href="/venues/obriens/booking">For artists</a>', html)
        html = self.view(self.obriens).content.decode()
        self.assertIn('<a href="/venues/obriens/booking" aria-current="page">For artists</a>', html)
        self.assertIn('<a href="/venues/obriens">For fans</a>', html)

    def test_inactive_or_unknown_venue(self):
        Venue.objects.filter(pk=self.obriens.pk).update(is_active=False)
        self.assertEqual(self.view(self.obriens).status_code, 404)
        self.assertEqual(self.client.get("/venues/nope/booking").status_code, 404)

    def test_open_booking_with_a_link_and_notes(self):
        html = self.view(self.obriens).content.decode()
        self.assertIn("Takes open bookings", html)
        self.assertIn("<b>Submit an Artist</b><span class=\"venue-booking-meaning\">Send them your act and they&#x27;ll place you on a bill.</span>", html)
        self.assertIn('<dt>How to apply</dt><dd><a href="https://obriens.example/book"', html)
        self.assertIn("Email the booker with links.", html)
        self.assertIn("<dt>Open mic</dt><dd>No</dd>", html)
        self.assertIn("<dt>Books</dt><dd>Rock</dd>", html)

    def test_falls_back_to_the_website(self):
        Venue.objects.filter(pk=self.obriens.pk).update(booking_url="")
        self.assertContains(self.view(self.obriens), '<dt>How to apply</dt><dd><a href="https://obriens.example"')

    def test_not_known(self):
        v = venue("Mystery Room", booking_type=Venue.BookingType.UNKNOWN, genres=["Rock"])
        html = self.view(v).content.decode()
        self.assertIn("Not known", html)
        self.assertNotIn("<dt>Booking</dt>", html)

    def test_closed_booking(self):
        v = venue("Locals Bar", open_booking=False, booking_type=Venue.BookingType.LOCALS_ONLY, booking_notes="Locals only, sorry.")
        html = self.view(v).content.decode()
        self.assertIn("Doesn&#x27;t take open bookings", html)
        self.assertIn("<b>Locals Only</b>", html)
        self.assertIn("Locals only, sorry.", html)

    def test_nothing_known(self):
        v = venue("Blank Slate")
        html = self.view(v).content.decode()
        self.assertIn("No booking details are known yet.", html)
        self.assertNotIn("<dt>", html)

    def test_nothing_known_with_a_website(self):
        v = venue("Blank Site", website="https://blank.example")
        self.assertContains(self.view(v), 'Try <a href="https://blank.example"')

    def test_fan_page_leaves_booking_to_the_artist_view(self):
        html = self.client.get("/venues/obriens").content.decode()
        self.assertIn('href="/venues/obriens/booking"', html)
        self.assertNotIn("Email the booker", html)
        self.assertNotIn("https://obriens.example/book", html)

    def test_not_indexed_titled(self):
        html = self.view(self.obriens).content.decode()
        self.assertIn('<meta name="robots" content="noindex">', html)
        self.assertIn("<title>Booking O&#x27;Brien&#x27;s, Boston |", html)
        self.assertIn("How to book a show at O&#x27;Brien&#x27;s", html)

    def test_not_in_the_sitemap(self):
        xml = self.client.get("/sitemap.xml").content.decode()
        self.assertNotIn("/booking", xml)
        self.assertNotIn("/venues", xml)

    def test_trailing_slash(self):
        self.assertRedirects(self.client.get("/venues/obriens/booking/"), "/venues/obriens/booking", status_code=301, fetch_redirect_response=False)

    def test_a_reserved_looking_slug_doesnt_shadow(self):
        v = venue("Booking")
        self.assertEqual(v.slug, "booking")
        self.assertEqual(self.client.get("/venues/booking").status_code, 200)
        self.assertEqual(self.client.get("/venues/booking/booking").status_code, 200)
        self.assertEqual(self.client.get("/venues").status_code, 200)


class SingularAddressTestCase(TestCase):
    def test_the_singular_redirects(self):
        self.assertRedirects(self.client.get("/venue"), "/venues", status_code=301, fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/venue/"), "/venues", status_code=301, fetch_redirect_response=False)
        self.assertRedirects(self.client.get("/venue/obriens/"), "/venues/obriens", status_code=301, fetch_redirect_response=False)
