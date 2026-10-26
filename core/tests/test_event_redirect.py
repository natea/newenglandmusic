from core.models import Event, Venue
from django.test import TestCase
from django.utils import timezone


class EventRedirectTestCase(TestCase):
    def setUp(self):
        venue = Venue.objects.create(name="Paradise Rock Club")
        self.event = Event.objects.create(
            title="brutal prog matinée", venue=venue, starttime=timezone.now()
        )
        self.url = f"/event/{self.event.pk}"

    def test_request_without_a_user_agent(self):
        # some clients send no user agent at all; that used to be a server error
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"#event-{self.event.pk}")

    def test_telegram_waits_before_redirecting(self):
        # telegram's link preview needs a moment to read the page's tags
        response = self.client.get(
            self.url, HTTP_USER_AGENT="TelegramBot (like TwitterBot)"
        )
        self.assertContains(response, 'content="1;')

    def test_browsers_redirect_at_once(self):
        response = self.client.get(self.url, HTTP_USER_AGENT="Mozilla/5.0")
        self.assertContains(response, 'content="0;')
