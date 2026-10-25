from django.test import TestCase, override_settings


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
