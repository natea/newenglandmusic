from django.http import QueryDict
from django.test import TestCase
from django.utils import timezone

from core.geo_filters import area_q, offered_areas, parse_geo_filter
from core.models import Event, GeoArea, Venue

from .geo_fixture import load_geo_fixture


def venue(name, state, county="", city=""):
    return Venue.objects.create(name=name, state=state, county=county, city_town=city)


def members(label):
    area = GeoArea.objects.get(label=label)
    return set(Venue.objects.filter(area_q(area)).values_list("name", flat=True))


class AreaMembershipTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()

    def test_state_only_region(self):
        venue("Hartford Bar", "CT", "Hartford", "Hartford")
        venue("Cambridge Club", "MA", "Middlesex", "Cambridge")
        venue("Providence Hall", "RI", "Providence", "Providence")
        venue("Portsmouth Pub", "NH", "Rockingham", "Portsmouth")
        self.assertEqual(
            members("New England: South"), {"Hartford Bar", "Cambridge Club", "Providence Hall"}
        )

    def test_metro_matched_by_county(self):
        venue("Hyannis Hall", "MA", "Barnstable", "Hyannis")
        venue("Boston Bar", "MA", "Suffolk", "Boston")
        self.assertEqual(members("MA: Cape Cod"), {"Hyannis Hall"})

    def test_metro_matched_by_county_or_city(self):
        venue("Boston Bar", "MA", "Suffolk", "Boston")
        venue("Cambridge Club", "MA", "Middlesex", "Cambridge")
        venue("Lowell Lounge", "MA", "Middlesex", "Lowell")
        self.assertEqual(members("MA: Boston"), {"Boston Bar", "Cambridge Club"})

    def test_matching_ignores_case_and_whitespace(self):
        venue("Shouty Bar", "MA", "SUFFOLK", "boston")
        self.assertEqual(members("MA: Boston"), {"Shouty Bar"})

    def test_same_county_name_in_another_state(self):
        # MA: Central lists Worcester county and towns; Middlesex, CT is none of those
        venue("Middletown Bar", "CT", "Middlesex", "Middletown")
        venue("Worcester Hall", "MA", "Worcester", "Worcester")
        self.assertEqual(members("MA: Central"), {"Worcester Hall"})

    def test_nested_metros(self):
        venue("Cambridge Club", "MA", "Middlesex", "Cambridge")
        self.assertIn("Cambridge Club", members("MA: Boston"))
        self.assertIn("Cambridge Club", members("MA: Boston Metro Region"))

    def test_event_without_a_venue(self):
        cambridge = venue("Cambridge Club", "MA", "Middlesex", "Cambridge")
        now = timezone.now()
        Event.objects.create(title="at a venue", starttime=now, venue=cambridge)
        Event.objects.create(title="no venue", starttime=now, venue_override="a field somewhere")
        for area in GeoArea.objects.all():
            titles = set(
                Event.all_objects.filter(area_q(area, prefix="venue__")).values_list(
                    "title", flat=True
                )
            )
            self.assertNotIn("no venue", titles, area.label)


class OfferedAreasTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()

    def test_area_with_no_states_is_not_offered(self):
        self.assertTrue(GeoArea.objects.filter(label="Northeast Corridor").exists())
        labels = [area.label for area in offered_areas(GeoArea.Kind.REGION)]
        self.assertNotIn("Northeast Corridor", labels)

    def test_sheet_order(self):
        # the fixture lists New England: South before Tri-State
        labels = [area.label for area in offered_areas(GeoArea.Kind.REGION)]
        self.assertEqual(labels, ["New England: South", "Tri-State"])

    def test_slugs_come_from_labels(self):
        self.assertEqual(GeoArea.objects.get(label="MA: Boston Metro Region").slug, "ma-boston-metro-region")
        self.assertEqual(GeoArea.objects.get(label="New England: South").slug, "new-england-south")
        self.assertEqual(GeoArea.objects.get(label="Massachusetts").slug, "massachusetts")

    def test_short_label_drops_the_state(self):
        self.assertEqual(GeoArea.objects.get(label="MA: Cape Cod").short_label, "Cape Cod")
        self.assertEqual(GeoArea.objects.get(label="Tri-State").short_label, "Tri-State")


class ParseGeoFilterTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()

    def parse(self, query):
        return parse_geo_filter(QueryDict(query))

    def test_resolves_slugs(self):
        geo_filter = self.parse("region=tri-state&state=massachusetts&metro=ma-cape-cod")
        self.assertEqual(geo_filter.region.label, "Tri-State")
        self.assertEqual(geo_filter.state.label, "Massachusetts")
        self.assertEqual(geo_filter.metro.label, "MA: Cape Cod")
        self.assertEqual(
            geo_filter.query_string, "region=tri-state&state=massachusetts&metro=ma-cape-cod"
        )

    def test_unknown_slug_is_dropped(self):
        geo_filter = self.parse("state=atlantis&metro=ma-cape-cod")
        self.assertIsNone(geo_filter.state)
        self.assertEqual(geo_filter.metro.label, "MA: Cape Cod")

    def test_area_with_no_states_is_dropped(self):
        self.assertFalse(self.parse("region=northeast-corridor"))

    def test_metro_from_another_state_is_dropped(self):
        geo_filter = self.parse("state=vermont&metro=ma-cape-cod")
        self.assertEqual(geo_filter.state.label, "Vermont")
        self.assertIsNone(geo_filter.metro)
        self.assertEqual(geo_filter.query_string, "state=vermont")

    def test_empty_values_are_no_filter(self):
        self.assertFalse(self.parse("region=&state=&metro="))

    def test_filters_are_anded(self):
        venue("Boston Bar", "MA", "Suffolk", "Boston")
        venue("Burlington Bar", "VT", "Chittenden", "Burlington")
        geo_filter = self.parse("region=new-england-south&state=vermont")
        self.assertFalse(Venue.objects.filter(geo_filter.q()).exists())
        geo_filter = self.parse("region=new-england-south&state=massachusetts")
        self.assertEqual(
            set(Venue.objects.filter(geo_filter.q()).values_list("name", flat=True)), {"Boston Bar"}
        )
