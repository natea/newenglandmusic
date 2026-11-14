"""
posthog and goatcounter on the site's pages (add-posthog-analytics): loaded only when their
settings are set, never in the admin, and described on the privacy page. nothing here reaches
either service: the tests read the html.
"""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

ON = {"POSTHOG_PROJECT_TOKEN": "phc_test_token", "POSTHOG_HOST": "https://eu.i.posthog.com"}


class PostHogTestCase(TestCase):
    @override_settings(**ON)
    def test_switched_on(self):
        response = self.client.get("/")
        self.assertContains(response, 'posthog.init("phc_test_token", {')
        self.assertContains(response, 'api_host: "https://eu.i.posthog.com"')
        self.assertContains(response, 'person_profiles: "identified_only"')

    @override_settings(POSTHOG_PROJECT_TOKEN="")
    def test_switched_off(self):
        response = self.client.get("/")
        self.assertNotContains(response, "posthog.init")
        self.assertNotContains(response, "i.posthog.com")

    @override_settings(**ON)
    def test_not_in_the_admin(self):
        User.objects.create_superuser("editor", "editor@example.org", "pw")
        self.client.login(username="editor", password="pw")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "posthog")

    @override_settings(**ON)
    def test_no_session_recording(self):
        self.assertContains(self.client.get("/"), "disable_session_recording: true")

    @override_settings(POSTHOG_PROJECT_TOKEN='phc_"</script>', POSTHOG_HOST="https://us.i.posthog.com")
    def test_the_token_is_escaped(self):
        html = self.client.get("/").content.decode()
        self.assertNotIn('phc_"</script>', html)
        self.assertIn("phc_\\u0022\\u003C/script\\u003E", html)

    @override_settings(**ON)
    def test_the_privacy_page_describes_it(self):
        response = self.client.get("/privacy")
        self.assertContains(response, "uses PostHog")
        self.assertContains(response, "sets a cookie")
        self.assertContains(response, "approximate city and region from your IP address, then discards the address")
        self.assertContains(response, "no names, email addresses, IP addresses or recordings of your visit")
        self.assertContains(response, 'id="analytics-toggle"')

    @override_settings(POSTHOG_PROJECT_TOKEN="")
    def test_no_posthog_text_without_it(self):
        response = self.client.get("/privacy")
        self.assertNotContains(response, "PostHog")
        self.assertNotContains(response, "analytics-toggle")


class GoatCounterTestCase(TestCase):
    @override_settings(GOATCOUNTER_CODE="stagehopper")
    def test_goatcounter_switched_on(self):
        response = self.client.get("/")
        self.assertContains(response, 'data-goatcounter="https://stagehopper.goatcounter.com/count"')
        self.assertContains(response, 'src="//gc.zgo.at/count.js"')

    @override_settings(GOATCOUNTER_CODE="")
    def test_goatcounter_switched_off(self):
        self.assertNotContains(self.client.get("/"), "goatcounter")
