import datetime
from urllib.parse import urlencode

from django.test import TestCase
from django.utils import timezone

from core import digest
from core.digest import send_window
from core.models import DigestChoice, Event, GeoArea, Subscriber, Venue

from .geo_fixture import load_geo_fixture

SEND_DAY = datetime.date(2026, 11, 5)
NOON = datetime.time(12, 0)


def at(days, hour=20):
    return datetime.datetime.combine(SEND_DAY + datetime.timedelta(days=days), datetime.time(hour), tzinfo=digest.NEW_YORK)


class SelectionTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()
        self.subscriber = Subscriber.objects.create(email="fan@example.com", confirmed_at=timezone.now())
        self.window = send_window(SEND_DAY)
        # zip-like point near Cambridge; venues 6 and 14 miles away by the sheet's coordinates
        self.point = (42.373, -71.119)
        self.near6 = Venue.objects.create(name="Six", state="MA", city_town="Somerville", latitude=42.46, longitude=-71.119)
        self.near14 = Venue.objects.create(name="Fourteen", state="MA", city_town="Lowell", latitude=42.576, longitude=-71.119)
        self.vermont = Venue.objects.create(name="Vermont Hall", state="VT", city_town="Burlington", latitude=44.47, longitude=-73.2)
        self.portland = Venue.objects.create(name="Portland Hall", state="ME", city_town="Portland", latitude=43.66, longitude=-70.25)
        self.nowhere = Venue.objects.create(name="Unplaced", state="NH", city_town="Concord")

    def event(self, venue, title=None, when=None, **extra):
        return Event.objects.create(title=title or f"show at {venue.name}", starttime=when or at(1), venue=venue, **extra)

    def choose(self, kind, **fields):
        return DigestChoice.objects.create(subscriber=self.subscriber, kind=kind, **fields)

    def selected(self):
        return {event.title for event in digest.events_for(self.subscriber, self.window)}

    def test_area_choice(self):
        self.choose("area", area_query="state=vermont")
        self.event(self.vermont)
        self.event(self.near6)
        self.assertEqual(self.selected(), {"show at Vermont Hall"})

    def test_all_of_the_northeast(self):
        self.choose("area", area_query="all=1")
        for venue in (self.vermont, self.near6, self.nowhere):
            self.event(venue)
        self.assertEqual(len(self.selected()), 3)

    def test_distance_choice_6_and_14_miles(self):
        self.choose("near", label="02139", latitude=self.point[0], longitude=self.point[1], miles=10)
        self.event(self.near6)
        self.event(self.near14)
        self.assertEqual(self.selected(), {"show at Six"})

    def test_venue_without_coordinates_is_never_near(self):
        self.choose("near", label="x", latitude=self.point[0], longitude=self.point[1], miles=100)
        self.event(self.nowhere)
        self.assertEqual(self.selected(), set())

    def test_distance_uses_the_confident_place_location(self):
        self.near14.place_lookup_status = Venue.PlaceLookupStatus.CONFIDENT
        self.near14.place_latitude, self.near14.place_longitude = 42.375, -71.12
        self.near14.save()
        self.choose("near", label="x", latitude=self.point[0], longitude=self.point[1], miles=5)
        self.event(self.near14)
        self.assertEqual(self.selected(), {"show at Fourteen"})

    def test_followed_town_and_venue(self):
        self.choose("town", town="somerville", state="MA")
        self.choose("venue", venue=self.portland)
        for venue in (self.near6, self.portland, self.near14, self.vermont):
            self.event(venue)
        self.assertEqual(self.selected(), {"show at Six", "show at Portland Hall"})

    def test_union_lists_an_event_once(self):
        self.choose("area", area_query="state=vermont")
        self.choose("venue", venue=self.vermont)
        self.choose("town", town="Burlington", state="VT")
        self.event(self.vermont)
        self.assertEqual(len(digest.events_for(self.subscriber, self.window)), 1)

    def test_unapproved_event_is_not_selected(self):
        self.choose("venue", venue=self.vermont)
        self.event(self.vermont, is_approved=False)
        self.assertEqual(self.selected(), set())

    def test_stale_area_selects_nothing(self):
        self.choose("area", area_query="state=atlantis")
        self.event(self.vermont)
        self.assertEqual(self.selected(), set())
        self.assertTrue(digest.is_stale(self.subscriber.choices.get()))

    def test_empty_area_selects_nothing_not_everything(self):
        self.choose("area", area_query="")
        self.event(self.vermont)
        self.assertEqual(self.selected(), set())

    def test_partly_vanished_area_selects_nothing(self):
        # a dropped metro would parse to the whole state, and a renamed town to the whole metro
        self.event(self.near6)
        self.event(self.vermont)
        for query in (
            "state=massachusetts&metro=ma-gone-metro",
            "metro=ma-north-of-the-charles&town=Somerville, MA&town=Renamedville, MA",
        ):
            DigestChoice.objects.all().delete()
            choice = self.choose("area", area_query=query)
            self.assertTrue(digest.is_stale(choice), query)
            self.assertEqual(self.selected(), set(), query)

    def test_metro_narrowed_to_towns(self):
        query = urlencode([("metro", "ma-north-of-the-charles"), ("town", "Somerville, MA")])
        self.choose("area", area_query=query)
        self.near6.county = "Middlesex"
        self.near6.save()
        self.event(self.near6)
        self.event(Venue.objects.create(name="Boston Hall", state="MA", city_town="Boston"))
        self.assertEqual(self.selected(), {"show at Six"})
        self.assertFalse(digest.is_stale(self.subscriber.choices.get()))

    def test_null_start_time_is_left_out(self):
        self.choose("venue", venue=self.vermont)
        Event.objects.create(title="undated", starttime=None, venue=self.vermont)
        self.assertEqual(self.selected(), set())

    def test_window_runs_from_the_send_day_to_the_seventh_day_after(self):
        self.choose("venue", venue=self.vermont)
        self.event(self.vermont, "before", at(-1, 23))
        self.event(self.vermont, "day 0", at(0, 0))
        self.event(self.vermont, "day 7", at(7, 23))
        self.event(self.vermont, "day 8", at(8, 0))
        self.assertEqual(self.selected(), {"day 0", "day 7"})

    def test_cancelled_events_are_left_out(self):
        self.choose("venue", venue=self.vermont)
        self.event(self.vermont, is_cancelled=True)
        self.assertEqual(self.selected(), set())

    def test_no_choices_select_nothing(self):
        self.event(self.vermont)
        self.assertEqual(self.selected(), set())

    def test_week_is_the_monday_on_or_before(self):
        self.assertEqual(digest.week_of(datetime.date(2026, 11, 8)), datetime.date(2026, 11, 2))
        self.assertEqual(digest.week_of(datetime.date(2026, 11, 2)), datetime.date(2026, 11, 2))


class NewEnglandOnlyTestCase(SelectionTestCase):
    def test_all_areas_means_new_england(self):
        # like the listings, the weekly email holds only new england's shows
        self.choose("area", area_query=digest.ALL_AREAS)
        self.event(self.vermont)
        self.event(Venue.objects.create(name="Albany Hall", state="NY", city_town="Albany"))
        self.assertEqual(self.selected(), {"show at Vermont Hall"})
