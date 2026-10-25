import uuid
from urllib.parse import parse_qs, urlparse

from core.models import Event, Venue
from django.test import TestCase
from django.utils import timezone


class EventCalendarLinksTestCase(TestCase):
    def setUp(self):
        self.venue = Venue.objects.create(
            name=f"venue {uuid.uuid4()}", city_town="Hartford", state="CT"
        )
        self.event = Event.objects.create(
            title=f"event {uuid.uuid4()}", starttime=timezone.now(), venue=self.venue
        )

    def test_gcal_link_includes_venue_location(self):
        response = self.client.get(f"/event/{self.event.pk}/gcal")
        self.assertEqual(response.status_code, 302)
        params = parse_qs(urlparse(response["Location"]).query)
        self.assertEqual(params["location"][0], f"{self.venue.name}, Hartford, CT")
        self.assertEqual(params["text"][0], f"{self.event.title} [New England Music]")

    def test_ics_download_includes_venue_location(self):
        response = self.client.get(f"/event/{self.event.pk}/ics")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f"LOCATION:{self.venue.name}\\, Hartford\\, CT", content)
        self.assertIn(f"SUMMARY:{self.event.title} [New England Music]", content)
