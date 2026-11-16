"""a venue's own page at /venues/<slug> (add-venue-pages, venue-pages)"""

import datetime
from io import StringIO
from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from core.admin import VenueAdmin
from core.models import Event, Venue
from core.tests.geo_fixture import load_geo_fixture
from core.utils_datemath import NYCTZ


def at(days, hour=19, minute=0):
    now = timezone.now().astimezone(NYCTZ)
    return (now + datetime.timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)


@override_settings(SITE_URL="https://stagehopper.app")
class VenuePageTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()
        self.obriens = Venue.objects.create(
            sheet_id="V1", name="O'Brien's", city_town="Boston", state="MA", neighborhood="Allston",
            venue_type="Bar", size=Venue.Size.SMALL, genre_notes="Rock, punk, metal",
            open_booking=True, booking_url="https://obriens.example/booking", booking_type=Venue.BookingType.SUBMIT_SHOW,
            website="https://obrienspubboston.com/", age_policy="21+", accessibility_notes="Steps at the door",
            latitude=42.35, longitude=-71.13,
        )

    def page(self, venue):
        return self.client.get(f"/venues/{venue.slug}")


class WhichVenuesHaveAPageTestCase(VenuePageTestCase):
    def test_an_active_venue(self):
        self.assertEqual(self.obriens.slug, "obriens")
        response = self.client.get("/venues/obriens")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h1 class="act-tab" id="venue-name">O&#x27;Brien&#x27;s</h1>', html=False)

    def test_unknown_status_has_a_page(self):
        self.assertIsNone(self.obriens.is_active)
        self.assertEqual(self.page(self.obriens).status_code, 200)

    def test_two_venues_with_one_name(self):
        burlington = Venue.objects.create(sheet_id="V2", name="The Bar", city_town="Burlington", state="VT")
        portland = Venue.objects.create(sheet_id="V3", name="The Bar", city_town="Portland", state="ME")
        self.assertNotEqual(burlington.slug, portland.slug)
        self.assertEqual((burlington.slug, portland.slug), ("the-bar", "the-bar-portland"))

    def test_inactive_or_unknown(self):
        Venue.objects.filter(pk=self.obriens.pk).update(is_active=False)
        self.assertEqual(self.client.get("/venues/obriens").status_code, 404)
        self.assertEqual(self.client.get("/venues/no-such-venue").status_code, 404)

    def test_outside_new_england(self):
        bowery = Venue.objects.create(sheet_id="V4", name="Bowery Ballroom", city_town="New York", state="NY")
        self.assertEqual(self.page(bowery).status_code, 404)

    def test_a_renamed_venue(self):
        self.obriens.name = "O'Brien's Pub"
        self.obriens.save()
        self.obriens.refresh_from_db()
        self.assertEqual(self.obriens.slug, "obriens")

    def test_added_in_the_admin(self):
        admin = User.objects.create_superuser("admin", "a@example.com", "pw")
        self.client.force_login(admin)
        self.client.post("/admin/core/venue/add/", {"name": "Lilypad", "city_town": "Cambridge", "state": "MA", "sheet_id": "V9"})
        self.assertEqual(Venue.objects.get(name="Lilypad").slug, "lilypad")

    def test_an_editor_can_change_the_slug(self):
        self.obriens.slug = "obriens-pub"
        self.obriens.save()
        self.assertEqual(self.client.get("/venues/obriens-pub").status_code, 200)

    def test_the_sheet_import_leaves_the_slug(self):
        from core.management.commands import sync_venues_from_gsheets as sync

        row = {key: "" for key in sync.REQUIRED_COLUMNS} if hasattr(sync, "REQUIRED_COLUMNS") else None
        fields = {"name": "O'Brien's Pub"}
        with mock.patch.object(sync, "venue_fields_from_row", return_value=fields):
            Venue.objects.update_or_create(sheet_id="V1", defaults=sync.venue_fields_from_row(row))
        self.obriens.refresh_from_db()
        self.assertEqual((self.obriens.name, self.obriens.slug), ("O'Brien's Pub", "obriens"))


class TheBillTestCase(VenuePageTestCase):
    def show(self, title, artists="", **fields):
        return Event.all_objects.create(title=title, artists=artists, venue=self.obriens, **fields)

    def test_nights_in_order(self):
        armus = self.show("Armus", starttime=at(2))
        motorhead = self.show("Motörhead", starttime=at(1, 19))
        subfobias = self.show("Subfobias", "Unabomber, Militia Rashad", starttime=at(1, 14))
        html = self.page(self.obriens).content.decode()
        positions = [html.index(f'href="/event/{e.pk}"') for e in (subfobias, motorhead, armus)]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('<b>Subfobias</b><span class="venue-with">with Unabomber, Militia Rashad</span>', html)
        self.assertIn("3 shows through", html)

    def test_todays_nights_are_marked(self):
        tonight = self.show("Tonight Band", starttime=at(0, 23, 30) if at(0, 23, 30) > timezone.now() else timezone.now() + datetime.timedelta(minutes=5))
        later = self.show("Later Band", starttime=at(3))
        html = self.page(self.obriens).content.decode()
        tonight_row = html[:html.index(f'href="/event/{tonight.pk}"')].rsplit("<li", 1)[1]
        later_row = html[:html.index(f'href="/event/{later.pk}"')].rsplit("<li", 1)[1]
        self.assertIn("is-tonight", tonight_row)
        self.assertNotIn("is-tonight", later_row)

    def test_unapproved_shows(self):
        hidden = self.show("Hidden Band", starttime=at(2), is_approved=False)
        self.assertNotContains(self.page(self.obriens), f"/event/{hidden.pk}")

    def test_nothing_coming_up(self):
        self.show("Old Band", starttime=at(-3))
        html = self.page(self.obriens).content.decode()
        self.assertIn("No upcoming shows listed.", html)
        self.assertNotIn("The bill", html)


class FactLineTestCase(VenuePageTestCase):
    def test_open_booking(self):
        html = self.page(self.obriens).content.decode()
        self.assertIn('<a class="venue-book" href="https://obriens.example/booking" target="_blank" rel="noopener">Open booking ›</a>', html)
        self.assertIn("<b>Small bar</b> · Allston, Boston, MA", html)
        self.assertIn('<span class="venue-books">Rock, punk, metal</span>', html)

    def test_open_booking_without_a_link(self):
        Venue.objects.filter(pk=self.obriens.pk).update(booking_url="")
        self.assertContains(self.page(self.obriens), '<a class="venue-book" href="#playing-here">Open booking ›</a>')

    def test_closed_booking(self):
        Venue.objects.filter(pk=self.obriens.pk).update(open_booking=False)
        self.assertNotContains(self.page(self.obriens), 'class="venue-book"')

    def test_the_sub_region(self):
        somerville = Venue.objects.create(sheet_id="V5", name="ONCE Ballroom", city_town="Somerville", state="MA")
        self.assertContains(self.page(somerville), '<a href="/?metro=ma-north-of-the-charles">North of the Charles</a>')

    def test_no_sub_region_outside_massachusetts(self):
        vermont = Venue.objects.create(sheet_id="V6", name="Higher Ground", city_town="South Burlington", state="VT")
        self.assertNotContains(self.page(vermont), "/?metro=")


class SectionsTestCase(VenuePageTestCase):
    def test_playing_and_getting_here(self):
        html = self.page(self.obriens).content.decode()
        self.assertIn('<h2 id="playing-here">Playing here</h2>', html)
        self.assertIn("<dt>Booking</dt><dd>Submit a Show</dd>", html)
        self.assertIn("<dt>Size</dt><dd>Small (&lt;100)</dd>", html)
        self.assertIn('<h2 id="getting-here">Getting here</h2>', html)
        self.assertIn("<dt>Ages</dt><dd>21+</dd>", html)
        self.assertIn('<a href="https://obrienspubboston.com/" target="_blank" rel="noopener">obrienspubboston.com</a>', html)

    def test_a_sparse_venue(self):
        sparse = Venue.objects.create(sheet_id="V7", name="The Shed", city_town="Brattleboro", state="VT", website="https://shed.example")
        html = self.page(sparse).content.decode()
        self.assertIn("<dt>Where</dt><dd>Brattleboro, VT</dd>", html)
        self.assertIn("shed.example", html)
        self.assertNotIn("Playing here", html)
        self.assertNotIn("<dt>Ages</dt>", html)

    def test_unknown_yes_or_no_isnt_drawn(self):
        html = self.page(self.obriens).content.decode()
        self.assertNotIn("Family-friendly", html)
        Venue.objects.filter(pk=self.obriens.pk).update(family_friendly=False)
        self.assertIn("<dt>Family-friendly</dt><dd>No</dd>", self.page(self.obriens).content.decode())


class LocationAndLinksTestCase(VenuePageTestCase):
    def test_location(self):
        html = self.page(self.obriens).content.decode()
        self.assertIn("Allston, Boston, MA", html)
        self.assertIn('href="https://www.google.com/maps/search/?api=1&amp;query=42.35,-71.13" target="_blank" rel="noopener">Map', html)
        self.assertNotIn("<iframe", html)
        self.assertNotIn("maps.googleapis", html)

    def test_from_an_event_page(self):
        event = Event.all_objects.create(title="Armus", venue=self.obriens, starttime=at(2))
        self.assertContains(self.client.get(f"/event/{event.pk}"), '<a href="/venues/obriens">O&#x27;Brien&#x27;s</a>')

    def test_no_link_to_a_venue_without_a_page(self):
        bowery = Venue.objects.create(sheet_id="V8", name="Bowery Ballroom", city_town="New York", state="NY")
        event = Event.all_objects.create(title="Armus", venue=bowery, starttime=at(2))
        self.assertNotContains(self.client.get(f"/event/{event.pk}"), "/venues/")

    def test_view_on_site_in_the_admin(self):
        self.assertEqual(self.obriens.get_absolute_url(), "/venues/obriens")
        admin = VenueAdmin(Venue, AdminSite())
        self.assertTrue(admin.view_on_site)
        user = User.objects.create_superuser("admin", "a@example.com", "pw")
        self.client.force_login(user)
        self.assertContains(self.client.get(f"/admin/core/venue/{self.obriens.pk}/change/"), "View on site")

    def test_can_be_indexed(self):
        html = self.page(self.obriens).content.decode()
        self.assertNotIn("noindex", html)
        self.assertIn('<link rel="canonical" href="https://stagehopper.app/venues/obriens">', html)

    def test_title_and_description(self):
        html = self.page(self.obriens).content.decode()
        self.assertIn("<title>O&#x27;Brien&#x27;s, Boston |", html)
        self.assertIn("upcoming shows, and how to book it.", html)
