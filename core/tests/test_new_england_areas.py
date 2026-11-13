"""
the site offers only the areas wholly inside New England; the admin keeps every one, and an old
link, cookie or feed naming a removed area is ignored like any unknown area
"""

from unittest import mock

from core.admin import EventAdmin, VenueAdmin
from core.geo_filters import COOKIE_NAME, NEW_ENGLAND_STATES, metro_groups, offered_areas, parse_geo_filter
from core.models import AllEventProxy, Event, GeoArea, Venue
from core.tests.geo_fixture import load_geo_fixture
from core.tests.new_england_fixture import new_england_venue
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.http import QueryDict
from django.test import RequestFactory, TestCase
from django.utils import timezone
from icalendar import Calendar

Kind = GeoArea.Kind


def area(kind, label, states, home_state="", **rules):
    return GeoArea.objects.create(
        kind=kind, sheet_id=f"{kind}_{label}", label=label, slug=label.lower().replace(": ", "-").replace(" ", "-"),
        home_state=home_state, states=states, sort_order=GeoArea.objects.count(), **rules,
    )


class SiteOptionsTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()
        area(Kind.REGION, "Chesapeake Bay", ["dc", "md"])
        area(Kind.REGION, "Mid-Atlantic", ["ny", "nj", "pa"])
        for label, code in (("DC", "dc"), ("Delaware", "de"), ("Maryland", "md"), ("New Jersey", "nj"),
                            ("New York", "ny"), ("Pennsylvania", "pa"), ("Connecticut", "ct"), ("Maine", "me"),
                            ("New Hampshire", "nh")):
            area(Kind.STATE, label, [code], code.upper())
        area(Kind.METRO, "NY: Hudson Valley", ["ny"], "NY")
        area(Kind.METRO, "CT: Hartford", ["ct"], "CT")

    def labels(self, kind, **kwargs):
        return [a.label for a in offered_areas(kind, new_england_only=True, **kwargs)]

    def test_regions_outside_new_england(self):
        # Tri-State has a state outside New England, so it goes with the others
        self.assertEqual(self.labels(Kind.REGION), ["New England: South"])
        self.assertIn("Tri-State", [a.label for a in offered_areas(Kind.REGION)])

    def test_states_outside_new_england(self):
        self.assertEqual(
            self.labels(Kind.STATE),
            ["Massachusetts", "Rhode Island", "Vermont", "Connecticut", "Maine", "New Hampshire"],
        )

    def test_metros_of_removed_states(self):
        groups = metro_groups()
        self.assertNotIn("NY: Hudson Valley", [metro.label for _, metros in groups for metro in metros])
        self.assertEqual([label for label, _ in groups], ["Massachusetts", "Vermont", "Connecticut"])

    def test_area_with_no_states(self):
        self.assertNotIn("Northeast Corridor", self.labels(Kind.REGION))

    def test_sheet_order(self):
        self.assertEqual(self.labels(Kind.REGION)[0], "New England: South")
        self.assertEqual(self.labels(Kind.STATE)[:3], ["Massachusetts", "Rhode Island", "Vermont"])

    def test_lowercase_sheet_states(self):
        self.assertTrue(all(state == state.lower() for a in GeoArea.objects.all() for state in a.states))
        self.assertEqual(len(self.labels(Kind.METRO)), 7)

    def test_the_homepage_form_offers_them(self):
        response = self.client.get("/")
        self.assertEqual([a.label for a in response.context["state_options"]][:2], ["Massachusetts", "Rhode Island"])
        self.assertNotContains(response, "tri-state")
        self.assertNotContains(response, "new-york")
        self.assertNotContains(response, "hudson-valley")

    def test_widening_the_list_offers_new_york(self):
        with mock.patch("core.geo_filters.NEW_ENGLAND_STATES", [*NEW_ENGLAND_STATES, "NY"]):
            self.assertIn("New York", self.labels(Kind.STATE))
            self.assertIn("NY: Hudson Valley", [m.label for _, ms in metro_groups() for m in ms])

    def test_a_town_link_under_the_flag(self):
        Venue.objects.create(name="Cambridge Club", state="MA", county="Middlesex", city_town="Cambridge")
        query = QueryDict("metro=ma-boston&town=Cambridge, MA")
        self.assertEqual(parse_geo_filter(query, new_england_only=True).towns, [("Cambridge", "MA")])

    def test_a_venue_with_a_lowercase_state_has_no_town(self):
        Venue.objects.create(name="Lower Hall", state="ma", county="Suffolk", city_town="Boston")
        query = QueryDict("metro=ma-boston&town=Boston, ma")
        self.assertEqual(parse_geo_filter(query, new_england_only=True).towns, [])


class AdminSidebarTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()
        area(Kind.STATE, "New York", ["ny"], "NY")
        area(Kind.METRO, "NY: Hudson Valley", ["ny"], "NY", cities=["beacon"])
        self.user = User.objects.create_superuser("admin", "a@example.com", "pw")
        soon = timezone.now() + timezone.timedelta(days=3)
        for name, state, city in (("Beacon Hall", "NY", "Beacon"), ("Hartford Hall", "CT", "Hartford")):
            venue = Venue.objects.create(name=name, state=state, city_town=city)
            Event.objects.create(title=name, starttime=soon, venue=venue)

    def changelist(self, admin, url, params):
        request = RequestFactory().get(url, params)
        request.user = self.user
        return request, admin.get_changelist_instance(request)

    def test_admin_sidebar_keeps_every_area(self):
        request, changelist = self.changelist(VenueAdmin(Venue, AdminSite()), "/admin/core/venue/", {})
        choices = {spec.title: [label for _, label in spec.lookup_choices] for spec in changelist.filter_specs
                   if spec.title in ("region", "state", "metro area")}
        self.assertIn("Tri-State", choices["region"])
        self.assertIn("New York", choices["state"])
        self.assertIn("NY: Hudson Valley", choices["metro area"])

    def test_filtering_still_resolves(self):
        admin = EventAdmin(AllEventProxy, AdminSite())
        for params in ({"region": "tri-state"}, {"state": "new-york"}, {"metro": "ny-hudson-valley"}):
            request, changelist = self.changelist(admin, "/admin/core/alleventproxy/", params)
            self.assertTrue({"Beacon Hall", "Hartford Hall"} & {e.title for e in changelist.get_queryset(request)}, params)
        request, changelist = self.changelist(admin, "/admin/core/alleventproxy/", {"state": "new-york"})
        self.assertEqual({e.title for e in changelist.get_queryset(request)}, {"Beacon Hall"})


class StaleLinksTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()
        area(Kind.STATE, "New York", ["ny"], "NY")
        area(Kind.REGION, "Mid-Atlantic", ["ny", "nj", "pa"])
        new_england_venue()
        Event.objects.create(
            title="boston show", starttime=timezone.now() + timezone.timedelta(minutes=30), venue=new_england_venue()
        )

    def test_old_link_to_new_york(self):
        response = self.client.get("/?state=new-york")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["geo_filter"].state)
        self.assertContains(response, "boston show")
        self.assertNotIn(COOKIE_NAME, response.cookies)

    def test_old_cookie(self):
        self.client.cookies[COOKIE_NAME] = "region=mid-atlantic"
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "boston show")
        self.assertEqual(response.cookies[COOKIE_NAME].value, "")

    def test_old_feed_subscription(self):
        response = self.client.get("/calendar.ics?state=new-york")
        self.assertEqual(response.status_code, 200)
        entries = Calendar.from_ical(response.content).walk("VEVENT")
        self.assertEqual([str(e["SUMMARY"]).split(" [")[0] for e in entries], ["boston show"])
