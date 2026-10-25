from unittest import mock

from core.models import Venue
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone


class AnalyticsTestCase(TestCase):
    @override_settings(GOOGLE_ANALYTICS_ID="", GOATCOUNTER_CODE="")
    def test_no_trackers_without_ids(self):
        response = self.client.get("/")
        self.assertNotContains(response, "googletagmanager.com")
        self.assertNotContains(response, "goatcounter")

    @override_settings(GOOGLE_ANALYTICS_ID="G-TEST123", GOATCOUNTER_CODE="mysite")
    def test_trackers_use_the_configured_ids(self):
        response = self.client.get("/")
        self.assertContains(response, "https://www.googletagmanager.com/gtag/js?id=G-TEST123")
        self.assertContains(response, "gtag('config', 'G-TEST123')")
        self.assertContains(response, 'data-goatcounter="https://mysite.goatcounter.com/count"')

    @override_settings(GOOGLE_ANALYTICS_ID="", GOATCOUNTER_CODE="mysite")
    def test_each_tracker_is_independent(self):
        response = self.client.get("/")
        self.assertContains(response, "mysite.goatcounter.com")
        self.assertNotContains(response, "googletagmanager.com")


class SiteSettingsTestCase(TestCase):
    @override_settings(CONTACT_EMAIL="hello@example.org")
    def test_event_form_shows_the_contact_email(self):
        response = self.client.get(reverse("submit_event"))
        self.assertContains(response, 'href="mailto:hello@example.org"')
        self.assertNotContains(response, "nyc-noise.com")

    @override_settings(CONTACT_EMAIL="")
    def test_event_form_hides_the_flyer_note_without_an_email(self):
        response = self.client.get(reverse("submit_event"))
        self.assertNotContains(response, "mailto:")

    def test_share_links_use_the_site_url(self):
        response = self.client.get("/")
        self.assertContains(response, f'<meta property="og:url" content="{settings.SITE_URL}/">')
        self.assertNotContains(response, "nyc-noise.com")

    @override_settings(
        ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION=True,
        DEFAULT_FROM_EMAIL="events@example.org",
        JESSICA_EMAIL="hello@example.org",
    )
    def test_submission_email_uses_the_configured_addresses(self):
        venue = Venue.objects.create(name="The Venue")
        with mock.patch("core.views.event_submission.aws_mail_sender") as sender:
            self.client.post(
                reverse("submit_event"),
                {"starttime": timezone.now(), "title": "show", "venue": venue.pk},
            )
        kwargs = sender.send_email.call_args.kwargs
        self.assertEqual(kwargs["source"], "events@example.org")
        self.assertEqual(kwargs["destination"], "hello@example.org")
