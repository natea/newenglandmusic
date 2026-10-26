from core.admin import EventAdmin, VenueAdmin
from core.models import AllEventProxy, Event, Venue
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.utils import timezone

from .geo_fixture import load_geo_fixture


class AdminGeoFilterTestCase(TestCase):
    def setUp(self):
        load_geo_fixture()
        self.user = User.objects.create_superuser("admin", "a@example.com", "pw")
        soon = timezone.now() + timezone.timedelta(days=3)
        for name, state, county, city in [
            ("Cambridge Club", "MA", "Middlesex", "Cambridge"),
            ("Hyannis Hall", "MA", "Barnstable", "Hyannis"),
            ("Burlington Bar", "VT", "Chittenden", "Burlington"),
            ("Hartford Hall", "CT", "Hartford", "Hartford"),
            ("Brooklyn Bowl", "NY", "Kings", "Brooklyn"),
        ]:
            venue = Venue.objects.create(name=name, state=state, county=county, city_town=city)
            for approved in (True, False):
                Event.objects.create(
                    title=f"{name} {'approved' if approved else 'pending'}",
                    starttime=soon,
                    venue=venue,
                    is_approved=approved,
                )

    def changelist(self, model_admin, url, params):
        request = RequestFactory().get(url, params)
        request.user = self.user
        return request, model_admin.get_changelist_instance(request)

    def listed_events(self, **params):
        admin = EventAdmin(AllEventProxy, AdminSite())
        request, changelist = self.changelist(admin, "/admin/core/alleventproxy/", params)
        return {event.title for event in changelist.get_queryset(request)}

    def listed_venues(self, **params):
        admin = VenueAdmin(Venue, AdminSite())
        request, changelist = self.changelist(admin, "/admin/core/venue/", params)
        return {venue.name for venue in changelist.get_queryset(request)}

    def test_review_queue_for_one_metro(self):
        self.assertEqual(
            self.listed_events(metro="ma-boston-metro-region", is_approved__exact="0"),
            {"Cambridge Club pending"},
        )

    def test_filters_combine_with_each_other(self):
        self.assertEqual(
            self.listed_events(region="new-england-south", state="massachusetts"),
            {"Cambridge Club approved", "Cambridge Club pending", "Hyannis Hall approved", "Hyannis Hall pending"},
        )

    def test_venues_by_region(self):
        self.assertEqual(self.listed_venues(region="tri-state"), {"Hartford Hall", "Brooklyn Bowl"})

    def test_venues_by_state_and_metro(self):
        self.assertEqual(self.listed_venues(state="massachusetts"), {"Cambridge Club", "Hyannis Hall"})
        self.assertEqual(self.listed_venues(metro="ma-cape-cod"), {"Hyannis Hall"})

    def test_unknown_value_filters_nothing(self):
        self.assertEqual(len(self.listed_venues(state="atlantis")), 5)

    def test_admin_metro_list_follows_the_state(self):
        admin = VenueAdmin(Venue, AdminSite())
        request, changelist = self.changelist(admin, "/admin/core/venue/", {"state": "vermont"})
        metro_filter = next(spec for spec in changelist.filter_specs if spec.title == "metro area")
        self.assertEqual([label for _, label in metro_filter.lookup_choices], ["VT: North", "VT: South"])

    def test_sidebar_titles(self):
        admin = EventAdmin(AllEventProxy, AdminSite())
        request, changelist = self.changelist(admin, "/admin/core/alleventproxy/", {})
        titles = [spec.title for spec in changelist.filter_specs]
        for title in ("region", "state", "metro area"):
            self.assertIn(title, titles)

    def test_sidebar_counts_each_area(self):
        admin = VenueAdmin(Venue, AdminSite())
        request, changelist = self.changelist(admin, "/admin/core/venue/", {"_facets": "True"})
        state_filter = next(spec for spec in changelist.filter_specs if spec.title == "state")
        counts = {
            choice["display"] for choice in state_filter.choices(changelist)
        }
        self.assertIn("Massachusetts (2)", counts)
        self.assertIn("Vermont (1)", counts)
