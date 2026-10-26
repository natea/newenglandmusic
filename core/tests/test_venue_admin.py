from core.admin import EventAdmin, VenueAdmin
from core.models import Event, JobRun, Venue, VenueFetchStatus
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.forms.models import model_to_dict
from django.test import RequestFactory, TestCase
from django.utils import timezone


class VenueAdminTicketmasterTestCase(TestCase):
    def setUp(self):
        self.admin = VenueAdmin(Venue, AdminSite())
        self.request = RequestFactory().get("/admin/core/venue/")
        self.request.user = User.objects.create_superuser("admin", "a@example.com", "pw")
        self.linked = Venue.objects.create(name="Linked", ticketmaster_venue_id="KovZpZA11JtA")
        self.unlinked = Venue.objects.create(name="Unlinked")
        self.blank = Venue.objects.create(name="Blank", ticketmaster_venue_id="")

    def save_through_admin_form(self, venue, ticketmaster_venue_id):
        form_class = self.admin.get_form(self.request, venue)
        data = {k: v for k, v in model_to_dict(venue).items() if v is not None}
        data["genres"] = ",".join(venue.genres)
        data["ticketmaster_venue_id"] = ticketmaster_venue_id
        form = form_class(data, instance=venue)
        self.assertTrue(form.is_valid(), form.errors)
        return form.save()

    def test_admin_can_set_and_clear_the_link(self):
        venue = self.save_through_admin_form(self.unlinked, "Za5ju3rKuqZBnGN6QUVouRbTvq3T7dOnF")
        self.assertEqual(venue.ticketmaster_venue_id, "Za5ju3rKuqZBnGN6QUVouRbTvq3T7dOnF")
        venue = self.save_through_admin_form(venue, "")
        self.assertFalse(Venue.objects.get(pk=venue.pk).ticketmaster_venue_id)

    def test_field_is_in_the_admin_form(self):
        fields = [f for _, options in self.admin.fieldsets for f in options["fields"]]
        self.assertIn("ticketmaster_venue_id", fields)
        self.assertIn("ticketmaster_venue_id", self.admin.search_fields)

    def test_website_without_a_scheme_gets_https(self):
        venue = Venue.objects.get(pk=self.unlinked.pk)
        venue.website = "example.com"
        venue = self.save_through_admin_form(venue, "")
        self.assertEqual(Venue.objects.get(pk=venue.pk).website, "https://example.com")

    def test_explicit_http_website_is_kept(self):
        venue = Venue.objects.get(pk=self.unlinked.pk)
        venue.website = "http://example.com"
        venue = self.save_through_admin_form(venue, "")
        self.assertEqual(Venue.objects.get(pk=venue.pk).website, "http://example.com")

    def filtered(self, value):
        # go through the changelist, since django 5 passes filters lists where 4.2 passed strings
        request = RequestFactory().get("/admin/core/venue/", {"ticketmaster": value} if value else {})
        request.user = self.request.user
        changelist = self.admin.get_changelist_instance(request)
        return set(changelist.get_queryset(request))

    def test_linked_filter(self):
        self.assertEqual(self.filtered("yes"), {self.linked})
        self.assertEqual(self.filtered("no"), {self.unlinked, self.blank})
        self.assertEqual(len(self.filtered(None)), 3)


class VenueAdminPlaceTestCase(TestCase):
    def setUp(self):
        self.admin = VenueAdmin(Venue, AdminSite())
        self.request = RequestFactory().get("/admin/core/venue/")
        self.request.user = User.objects.create_superuser("admin", "a@example.com", "pw")
        self.review = Venue.objects.create(
            name="Paradise Rock Club",
            latitude=42.3529,
            longitude=-71.1321,
            place_lookup_status=Venue.PlaceLookupStatus.REVIEW,
            place_id="ChIJparadise",
            place_name="Paradise Rock Club",
            place_latitude=42.3519,
            place_longitude=-71.1195,
            place_business_status="OPERATIONAL",
        )
        self.closed = Venue.objects.create(
            name="Gone",
            place_lookup_status=Venue.PlaceLookupStatus.CONFIDENT,
            place_id="ChIJgone",
            place_business_status="CLOSED_PERMANENTLY",
        )
        self.not_found = Venue.objects.create(
            name="Nowhere", place_lookup_status=Venue.PlaceLookupStatus.NOT_FOUND
        )

    def changelist_ids(self, **params):
        request = RequestFactory().get("/admin/core/venue/", params)
        request.user = self.request.user
        changelist = self.admin.get_changelist_instance(request)
        return set(changelist.get_queryset(request).values_list("name", flat=True))

    def test_filters(self):
        self.assertEqual(self.changelist_ids(place_lookup_status__exact="review"), {"Paradise Rock Club"})
        self.assertEqual(
            self.changelist_ids(place_business_status__exact="CLOSED_PERMANENTLY"), {"Gone"}
        )

    def test_place_fields_are_in_the_admin_form(self):
        fields = [f for _, options in self.admin.fieldsets for f in options["fields"]]
        for field in ("place_lookup_status", "place_address", "place_latitude", "place_maps_url"):
            self.assertIn(field, fields)

    def test_confirming_a_match_puts_it_to_use(self):
        event = Event.objects.create(title="show", starttime=timezone.now(), venue=self.review)
        self.admin.mark_place_as_confident(self.request, Venue.objects.all())
        self.review.refresh_from_db()
        self.assertEqual(self.review.place_lookup_status, Venue.PlaceLookupStatus.CONFIDENT)
        self.assertEqual(self.review.exact_location, (42.3519, -71.1195))
        # the event's stored html has the new pin
        event = Event.all_objects.get(pk=event.pk)
        self.assertIn('data-venue-lnglat="-71.1195,42.3519"', event.baked_html_template)
        # a venue that was never found has nothing to confirm
        self.assertEqual(
            Venue.objects.get(pk=self.not_found.pk).place_lookup_status,
            Venue.PlaceLookupStatus.NOT_FOUND,
        )

    def test_clearing_a_lookup(self):
        self.admin.clear_place_lookup(self.request, Venue.objects.filter(pk=self.review.pk))
        self.review.refresh_from_db()
        self.assertEqual(self.review.place_lookup_status, "")
        self.assertEqual(self.review.place_id, "")
        self.assertIsNone(self.review.place_latitude)
        self.assertIsNone(self.review.place_looked_up_at)
        self.assertEqual(self.review.exact_location, (42.3529, -71.1321))


class EventAdminVenueLinkTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "a@example.com", "pw")
        self.client.force_login(self.user)
        self.venue = Venue.objects.create(name="Paradise <Rock> Club")
        Event.objects.create(title="with venue", starttime=timezone.now(), venue=self.venue)
        Event.objects.create(title="no venue", starttime=timezone.now())

    def test_venue_column_links_to_the_venue(self):
        response = self.client.get("/admin/core/alleventproxy/", {"starttime": "all"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'<a href="/admin/core/venue/{self.venue.pk}/change/">Paradise &lt;Rock&gt; Club</a>',
            html=True,
        )

    def test_venue_column_sorts_by_name(self):
        self.assertEqual(EventAdmin.get_venue_link.admin_order_field, "venue__name")


class VenueAdminFetchStatusTestCase(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        now = timezone.now()
        self.run = JobRun.objects.create(command="fetch_events", started_at=now)
        self.failing = Venue.objects.create(name="Off The Rails", sheet_id="V0316")
        self.empty = Venue.objects.create(name="Congress Square Park", sheet_id="V0369")
        self.working = Venue.objects.create(name="Bug Jar", sheet_id="V0591")
        self.never = Venue.objects.create(name="Lizard Lounge", sheet_id="V0142")
        for venue, upcoming, problems in (
            (self.failing, 0, ["failed: https://www.ticketweb.com/event/1 HttpError()"]),
            (self.empty, 0, []),
            (self.working, 8, []),
        ):
            VenueFetchStatus.objects.create(
                venue=venue,
                fetched_at=now,
                source="ticketing",
                found=upcoming,
                upcoming=upcoming,
                problems=problems,
                job_run=self.run,
            )

    def listed(self, state):
        response = self.client.get("/admin/core/venue/", {"fetch": state})
        return set(response.context["cl"].result_list)

    def test_filter_states(self):
        self.assertEqual(self.listed("problems"), {self.failing})
        self.assertEqual(self.listed("nothing"), {self.empty})
        self.assertEqual(self.listed("ok"), {self.working})
        self.assertEqual(self.listed("never"), {self.never})

    def test_filter_to_problem_venues_marks_them_red(self):
        response = self.client.get("/admin/core/venue/", {"fetch": "problems"})
        self.assertContains(
            response, '<strong style="color: #cf222e">problems (1)</strong>', html=True
        )

    def test_list_column(self):
        response = self.client.get("/admin/core/venue/")
        self.assertContains(response, "OK · 8 upcoming")
        self.assertContains(response, "nothing found")
        self.assertContains(response, "never fetched")

    def test_venue_page(self):
        page = self.client.get(f"/admin/core/venue/{self.failing.pk}/change/")
        self.assertContains(page, "ticketing · 0 found, 0 upcoming")
        self.assertContains(page, "failed: https://www.ticketweb.com/event/1 HttpError()")
        self.assertContains(page, f'href="/admin/core/jobrun/{self.run.pk}/change/"')

    def test_never_fetched_venue_page(self):
        page = self.client.get(f"/admin/core/venue/{self.never.pk}/change/")
        self.assertContains(page, "never fetched")
