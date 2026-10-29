import datetime
from io import StringIO

from core.models import Event, Venue
from core.tests.osm_fixture import FakeOsm, fixture
from django.contrib.auth.models import User
from django.core.management import call_command
from django.forms.models import model_to_dict
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

Source = Venue.NeighborhoodSource


class NeighborhoodAdminTestCase(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "a@example.com", "pw"))
        self.venue = Venue.objects.create(name="9:30 Club", city_town="Washington", state="DC", is_active=True, sheet_id="V0999")
        self.event = Event.objects.create(title="a show", starttime=timezone.now() + datetime.timedelta(days=2), venue=self.venue)

    def post(self, **changes):
        url = reverse("admin:core_venue_change", args=[self.venue.pk])
        form = self.client.get(url).context["adminform"].form
        data = {k: v for k, v in form.initial.items() if v is not None and not isinstance(v, (list, dict))}
        data.update({k: ("on" if v is True else v) for k, v in changes.items() if v is not False})
        response = self.client.post(url, data)
        self.assertIn(response.status_code, (200, 302), response.content[:500])
        return response

    def test_editor_sets_one_and_later_runs_keep_it(self):
        self.post(neighborhood="U Street")
        self.venue.refresh_from_db()
        self.assertEqual((self.venue.neighborhood, self.venue.neighborhood_source), ("U Street", Source.EDITOR))
        self.event.refresh_from_db()
        self.assertIn("Washington (U Street), DC", self.event.baked_html_template)
        osm = FakeOsm(searches={"9:30 Club": fixture("big_night_live.json")})
        with osm.patch():
            call_command("lookup_venue_neighborhoods", "--sheet-ids", "V0999", stdout=StringIO())
        self.assertEqual(osm.requests, [])
        self.venue.refresh_from_db()
        self.assertEqual(self.venue.neighborhood, "U Street")

    def test_no_neighborhood(self):
        Venue.objects.filter(pk=self.venue.pk).update(neighborhood="Shaw", neighborhood_source=Source.OVERPASS)
        self.post(no_neighborhood=True, neighborhood="Shaw")
        self.venue.refresh_from_db()
        self.assertEqual((self.venue.neighborhood, self.venue.neighborhood_source), ("", Source.EDITOR))

    def test_source_filter(self):
        response = self.client.get(reverse("admin:core_venue_changelist") + "?neighborhood_source__exact=editor")
        self.assertEqual(response.status_code, 200)
