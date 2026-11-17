"""
the venue list and a venue's artist view on a phone, in a real browser (add-venue-list): 390px
wide, nothing scrolls sideways; and the place form keeps the list's genre and open-booking
filters as it changes
"""

from core.models import Venue
from core.tests.browser import BrowserTestCase
from core.tests.geo_fixture import load_geo_fixture


class VenueListBrowserTestCase(BrowserTestCase):
    def setUp(self):
        super().setUp()
        load_geo_fixture()
        Venue.objects.create(
            sheet_id="V1", name="Middle East Downstairs, a Very Long Venue Name Indeed", city_town="Cambridge", state="MA",
            venue_type="Club", size=Venue.Size.MEDIUM, genres=["Rock", "Punk", "Hardcore", "Metal", "Experimental"],
            open_booking=True, booking_type=Venue.BookingType.SUBMIT_ARTIST, booking_url="https://example.org/a-very-long-booking-address/that-goes-on",
            booking_notes="Send links to https://example.org/a-very-long-press-kit-address-that-does-not-wrap-easily",
        )
        Venue.objects.create(sheet_id="V2", name="Higher Ground", city_town="South Burlington", state="VT", genres=["Jazz"])

    def phone(self, path):
        context = self.browser.new_context(viewport={"width": 390, "height": 844})
        self.addCleanup(context.close)
        context.route("**/*", self.only_the_test_server)
        _, page = self.open_page(path, context=context)
        return page

    def test_the_list_fits_a_phone(self):
        page = self.phone("/venues?open_booking=1")
        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)

    def test_the_artist_view_fits_a_phone(self):
        page = self.phone("/venues/middle-east-downstairs-a-very-long-venue-name-indeed/booking")
        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)

    def test_choosing_a_state_keeps_the_genre_and_open_booking(self):
        page = self.phone("/venues?genre=Jazz&open_booking=1")
        with page.expect_navigation():
            page.select_option("form.geoFilter select[name=state]", "vermont")
        self.assertIn("state=vermont", page.url)
        self.assertIn("genre=Jazz", page.url)
        self.assertIn("open_booking=1", page.url)

    def test_choosing_all_keeps_the_genre_and_forgets_the_place(self):
        page = self.phone("/venues?state=vermont&genre=Jazz")
        with page.expect_navigation():
            page.select_option("form.geoFilter select[name=state]", "")
        self.assertIn("genre=Jazz", page.url)
        self.assertNotIn("state=vermont", page.url)
        # the place is forgotten: a later visit isn't sent back to vermont
        page.goto(self.live_server_url + "/venues")
        self.assertNotIn("state=", page.url)
