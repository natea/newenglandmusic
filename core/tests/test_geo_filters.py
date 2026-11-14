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
    # the areas core/geo_areas.py defines, which every migrate loads

    def test_state_only_region(self):
        venue("Hartford Bar", "CT", "Hartford", "Hartford")
        venue("Cambridge Club", "MA", "Middlesex", "Cambridge")
        venue("Providence Hall", "RI", "Providence", "Providence")
        venue("Portsmouth Pub", "NH", "Rockingham", "Portsmouth")
        self.assertEqual(
            members("New England: South"), {"Hartford Bar", "Cambridge Club", "Providence Hall"}
        )

    def test_metro_matched_by_county(self):
        venue("Nashua Hall", "NH", "Hillsborough", "Nashua")
        venue("Hanover Bar", "NH", "Grafton", "Hanover")
        self.assertEqual(members("NH: South"), {"Nashua Hall"})

    def test_metro_matched_by_county_or_city(self):
        GeoArea.objects.create(
            kind="metro", sheet_id="metro_NY_Test", label="NY: Test", slug="ny-test", home_state="NY",
            states=["ny"], counties=["kings"], cities=["yonkers"],
        )
        venue("Brooklyn Bar", "NY", "Kings", "Brooklyn")
        venue("Yonkers Hall", "NY", "Westchester", "Yonkers")
        venue("White Plains Pub", "NY", "Westchester", "White Plains")
        self.assertEqual(members("NY: Test"), {"Brooklyn Bar", "Yonkers Hall"})

    def test_matching_ignores_case(self):
        venue("Shouty Bar", "MA", "MIDDLESEX", "SOMERVILLE")
        self.assertEqual(members("MA: North of the Charles"), {"Shouty Bar"})

    def test_same_county_name_in_another_state(self):
        # MA: MetroWest takes middlesex county by default; Middlesex, CT isn't in massachusetts
        venue("Middletown Bar", "CT", "Middlesex", "Middletown")
        venue("Woburn Hall", "MA", "Middlesex", "Woburn")
        self.assertEqual(members("MA: MetroWest"), {"Woburn Hall"})

    def test_nested_metros(self):
        venue("Brooklyn Bar", "NY", "Kings", "Brooklyn")
        self.assertIn("Brooklyn Bar", members("NY: NYC"))
        self.assertIn("Brooklyn Bar", members("NY: NYC Metro Region"))

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


def sub_regions_of(name):
    return [
        area.label
        for area in GeoArea.objects.exclude(group="")
        if Venue.objects.filter(area_q(area), name=name).exists()
    ]


class SubRegionTestCase(TestCase):
    """massachusetts's sub-regions (core/geo_areas.py): every venue in exactly one"""

    def boston(self, name, neighborhood, county="Suffolk"):
        return Venue.objects.create(name=name, state="MA", county=county, city_town="Boston", neighborhood=neighborhood)

    def test_a_listed_town(self):
        venue("Iron Horse", "MA", "Hampshire", "Northampton")
        self.assertEqual(sub_regions_of("Iron Horse"), ["MA: Pioneer Valley / Connecticut River Valley"])

    def test_a_boston_neighborhood(self):
        self.boston("Fenway Hall", "Fenway-Kenmore")
        venue("JP Bar", "MA", "Suffolk", "Jamaica Plain")
        self.assertEqual(sub_regions_of("Fenway Hall"), ["MA: Downtown & Central Boston"])
        self.assertEqual(sub_regions_of("JP Bar"), ["MA: Boston Neighborhoods"])

    def test_a_boston_neighborhood_given_with_boston(self):
        self.boston("Roxbury Club", "Roxbury")
        self.assertEqual(sub_regions_of("Roxbury Club"), ["MA: Boston Neighborhoods"])

    def test_a_town_the_list_doesnt_name(self):
        venue("Woburn Hall", "MA", "Middlesex", "Woburn")
        self.assertEqual(sub_regions_of("Woburn Hall"), ["MA: MetroWest"])

    def test_a_listed_town_beats_its_countys_default(self):
        # somerville is in middlesex, whose default is metrowest, but north of the charles lists it
        venue("Somerville Pub", "MA", "Middlesex", "Somerville")
        self.assertEqual(sub_regions_of("Somerville Pub"), ["MA: North of the Charles"])

    def test_boston_without_a_listed_neighborhood(self):
        self.boston("Plain Boston", "")
        self.boston("Odd Boston", "Somewhere New")
        self.assertEqual(sub_regions_of("Plain Boston"), ["MA: Downtown & Central Boston"])
        self.assertEqual(sub_regions_of("Odd Boston"), ["MA: Downtown & Central Boston"])

    def test_events_follow_their_venue(self):
        hall = venue("Iron Horse", "MA", "Hampshire", "Northampton")
        Event.objects.create(title="a show", starttime=timezone.now(), venue=hall)
        pioneer = GeoArea.objects.get(slug="ma-pioneer-valley-connecticut-river-valley")
        self.assertTrue(Event.all_objects.filter(area_q(pioneer, prefix="venue__")).exists())

    def test_every_venue_placed(self):
        # a venue in each county, by a listed town, a boston neighborhood, or only its county
        places = [
            ("Barnstable", "Hyannis"), ("Barnstable", "Harwich Port"), ("Berkshire", "Dalton"),
            ("Bristol", "Norton"), ("Dukes", "Oak Bluffs"), ("Essex", "Salisbury"), ("Franklin", "Montague"),
            ("Hampden", "Westfield"), ("Hampshire", "Amherst"), ("Middlesex", "Lowell"), ("Middlesex", "Woburn"),
            ("Nantucket", "Nantucket"), ("Norfolk", "Dedham"), ("Plymouth", "Hull"), ("Suffolk", "Allston"),
            ("Suffolk", "Revere"), ("Worcester", "Clinton"), ("Worcester", "Worcester"),
        ]
        for number, (county, town) in enumerate(places):
            venue(f"venue {number}", "MA", county, town)
        self.boston("Back Bay Bar", "Back Bay")
        for name in Venue.objects.values_list("name", flat=True):
            with self.subTest(name):
                self.assertEqual(len(sub_regions_of(name)), 1)


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
