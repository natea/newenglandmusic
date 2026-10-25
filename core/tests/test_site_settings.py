from unittest import mock

from core.models import Event, Venue
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


class MapsTestCase(TestCase):
    def setUp(self):
        venue = Venue.objects.create(name="The Venue", latitude=42.36, longitude=-71.06)
        Event.objects.create(title="show", starttime=timezone.now(), venue=venue, is_approved=True)

    @override_settings(PROTOMAPS_API_KEY="")
    def test_maps_are_hidden_without_a_key(self):
        response = self.client.get("/")
        self.assertContains(response, "show")
        self.assertNotContains(response, "SHOW MAP")
        self.assertNotContains(response, "maplibre")
        self.assertNotContains(response, "protomaps")

    @override_settings(PROTOMAPS_API_KEY="testkey123")
    def test_maps_use_the_configured_key_and_start_on_new_england_by_default(self):
        response = self.client.get("/")
        self.assertContains(response, "SHOW MAP")
        self.assertContains(response, "api.protomaps.com/styles/v4/light/en.json?key=testkey123")
        self.assertContains(response, "zoom: 6.0,")
        self.assertContains(response, "center: [-71.5, 43.2],")
        self.assertNotContains(response, "744c0d83a2202e0c")

    @override_settings(
        PROTOMAPS_API_KEY="testkey123", MAP_CENTER_LATITUDE=41.8, MAP_CENTER_LONGITUDE=-72.7, MAP_ZOOM=8
    )
    def test_starting_view_comes_from_settings(self):
        response = self.client.get("/")
        self.assertContains(response, "zoom: 8,")
        self.assertContains(response, "center: [-72.7, 41.8],")
