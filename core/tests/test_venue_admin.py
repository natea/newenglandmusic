from core.admin import LinkedToTicketmasterFilter, VenueAdmin
from core.models import Venue
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.forms.models import model_to_dict
from django.test import RequestFactory, TestCase


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

    def filtered(self, value):
        params = {"ticketmaster": value} if value else {}
        list_filter = LinkedToTicketmasterFilter(self.request, params, Venue, self.admin)
        return set(list_filter.queryset(self.request, Venue.objects.all()))

    def test_linked_filter(self):
        self.assertEqual(self.filtered("yes"), {self.linked})
        self.assertEqual(self.filtered("no"), {self.unlinked, self.blank})
        self.assertEqual(len(self.filtered(None)), 3)
