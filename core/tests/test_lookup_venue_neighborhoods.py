import datetime
from io import StringIO

from core.models import Event, JobRun, Venue
from core.tests.osm_fixture import FakeOsm, fixture, response
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

Source = Venue.NeighborhoodSource


def venue(name, town, state, **fields):
    return Venue.objects.create(name=name, city_town=town, state=state, is_active=True, **fields)


class LookupTestCase(TestCase):
    def setUp(self):
        self.osm = FakeOsm(
            searches={
                "Big Night Live": fixture("big_night_live.json"),
                "Century": fixture("century.json"),
                "Cafe Nine": fixture("cafe_nine.json"),
                "18th Ward Brewing": fixture("eighteenth_ward.json"),
                "The Sinclair": fixture("bus_stop_cambridge.json"),
            },
            overpass=[fixture("overpass_williamsburg.json")],
        )

    def run_command(self, *args):
        out = StringIO()
        with self.osm.patch():
            call_command("lookup_venue_neighborhoods", *args, stdout=out)
        return out.getvalue()

    def test_venue_found(self):
        big_night = venue("Big Night Live", "Boston", "MA")
        self.run_command()
        big_night.refresh_from_db()
        self.assertEqual((big_night.neighborhood, big_night.neighborhood_source), ("West End", Source.ADDRESS))
        self.assertIsNotNone(big_night.neighborhood_checked_at)

    def test_suburb_and_historic_district_rules(self):
        century, nine = venue("Century", "Philadelphia", "PA"), venue("Cafe Nine", "New Haven", "CT")
        self.run_command()
        century.refresh_from_db()
        nine.refresh_from_db()
        self.assertEqual((century.neighborhood, nine.neighborhood), ("South Philadelphia", "Dixwell"))

    def test_williamsburg_from_overpass(self):
        ward = venue("18th Ward Brewing", "Brooklyn", "NY")
        self.run_command()
        ward.refresh_from_db()
        self.assertEqual((ward.neighborhood, ward.neighborhood_source), ("Williamsburg", Source.OVERPASS))

    def test_overpass_busy_leaves_it_due(self):
        ward = venue("18th Ward Brewing", "Brooklyn", "NY")
        self.osm.overpass = [response(504)]
        out = self.run_command()
        ward.refresh_from_db()
        self.assertEqual((ward.neighborhood_source, ward.neighborhood_checked_at), ("", None))
        self.assertIn("left for the next run", out)

    def test_a_different_place_with_the_towns_name(self):
        sinclair = venue("The Sinclair", "Cambridge", "MA")
        self.run_command()
        sinclair.refresh_from_db()
        self.assertEqual((sinclair.neighborhood, sinclair.neighborhood_source), ("", Source.NONE))

    def test_google_data_never_sent(self):
        venue("Big Night Live", "Boston", "MA", place_id="ChIJsecretPlaceId123", place_latitude=42.36661, place_longitude=-71.06213,
              latitude=42.3601, longitude=-71.0589)
        self.run_command()
        for request in self.osm.requests:
            sent = f"{request.url} {request.params} {request.data}"
            for google in ("ChIJsecretPlaceId123", "42.36661", "-71.06213"):
                self.assertNotIn(google, sent)

    def test_nominatim_blocks(self):
        for i in range(3):
            venue(f"Hall {i}", "Boston", "MA")
        self.osm.searches["Hall 1"] = response(429)
        out = self.run_command()
        self.assertIn("stopped early, 2 venues left", out)
        self.assertEqual(Venue.objects.filter(neighborhood_checked_at__isnull=False).count(), 1)
        run = JobRun.objects.get(command="lookup_venue_neighborhoods")
        self.assertEqual(dict(run.summary)["left for the next run"], 2)

    def test_changed_rerenders_its_events(self):
        big_night = venue("Big Night Live", "Boston", "MA")
        event = Event.objects.create(title="a show", starttime=timezone.now() + datetime.timedelta(days=2), venue=big_night)
        event.refresh_from_db()
        self.assertNotIn("West End", event.baked_html_template)
        self.run_command()
        event.refresh_from_db()
        self.assertIn("Boston (West End), MA", event.baked_html_template)

    def test_due_rules(self):
        fresh = venue("Big Night Live", "Boston", "MA", neighborhood_checked_at=timezone.now() - datetime.timedelta(days=30))
        old = venue("Century", "Philadelphia", "PA", neighborhood_checked_at=timezone.now() - datetime.timedelta(days=400))
        edited = venue("Cafe Nine", "New Haven", "CT", neighborhood="Ninth Square", neighborhood_source=Source.EDITOR)
        self.run_command()
        asked = [r.params["q"].split(",")[0] for r in self.osm.requests if r.method == "GET"]
        self.assertEqual(asked, ["Century"])
        edited.refresh_from_db()
        self.assertEqual((edited.neighborhood, edited.neighborhood_source), ("Ninth Square", Source.EDITOR))
        # --sheet-ids looks up a venue whether due or not, but never an editor's
        fresh.sheet_id, edited.sheet_id = "V1", "V2"
        Venue.objects.filter(pk=fresh.pk).update(sheet_id="V1")
        Venue.objects.filter(pk=edited.pk).update(sheet_id="V2")
        self.osm.requests.clear()
        self.run_command("--sheet-ids", "V1,V2")
        self.assertEqual([r.params["q"].split(",")[0] for r in self.osm.requests if r.method == "GET"], ["Big Night Live"])

    def test_dry_run(self):
        big_night = venue("Big Night Live", "Boston", "MA")
        out = self.run_command("--dry-run")
        self.assertIn("Big Night Live (Boston, MA): West End (from the address)", out)
        big_night.refresh_from_db()
        self.assertEqual((big_night.neighborhood, big_night.neighborhood_checked_at), ("", None))


class EventLabelTestCase(TestCase):
    def baked(self, **venue_fields):
        v = Venue.objects.create(name="Big Night Live", city_town="Boston", state="MA", **venue_fields)
        event = Event.objects.create(title="a show", starttime=timezone.now() + datetime.timedelta(days=2), venue=v)
        event.refresh_from_db()
        return event.baked_html_template

    def test_shown(self):
        self.assertIn("<b>Big Night Live</b>, Boston (West End), MA", self.baked(neighborhood="West End"))

    def test_no_neighborhood(self):
        self.assertIn("<b>Big Night Live</b>, Boston, MA", self.baked())

    def test_venue_override(self):
        v = Venue.objects.create(name="Big Night Live", city_town="Boston", state="MA", neighborhood="West End")
        event = Event.objects.create(title="a show", starttime=timezone.now() + datetime.timedelta(days=2), venue=v, venue_override="a basement")
        event.refresh_from_db()
        self.assertNotIn("West End", event.baked_html_template)


class PointNeighborhoodTownsTestCase(LookupTestCase):
    def test_overpass_only_where_neighborhoods_are_points(self):
        danbury = venue("Sugar Hollow Taproom", "Danbury", "CT")
        self.osm.searches["Sugar Hollow Taproom"] = [{
            "name": "Sugar Hollow Taproom", "lat": "41.37", "lon": "-73.46",
            "address": {"hamlet": "Starrs Plain", "city": "Danbury", "state": "Connecticut", "ISO3166-2-lvl4": "US-CT"},
        }]
        out = self.run_command()
        self.assertEqual(self.osm.overpass_requests, [])
        self.assertIn("Sugar Hollow Taproom (Danbury, CT): - (found, no neighborhood)", out)
        danbury.refresh_from_db()
        self.assertEqual(danbury.neighborhood_source, Source.NONE)

    def test_not_on_openstreetmap(self):
        venue("Park City Music Hall", "Bridgeport", "CT")
        self.assertIn("Park City Music Hall (Bridgeport, CT): - (not on openstreetmap)", self.run_command())

    def test_state_option(self):
        venue("Big Night Live", "Boston", "MA")
        venue("Century", "Philadelphia", "PA")
        self.run_command("--state", "pa")
        self.assertEqual([r.params["q"] for r in self.osm.requests if r.method == "GET"], ["Century, Philadelphia, PA"])
