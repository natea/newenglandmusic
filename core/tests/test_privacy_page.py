from django.test import TestCase


class PrivacyPageTestCase(TestCase):
    def test_privacy_page(self):
        response = self.client.get("/privacy")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "YouTube API Services")
        self.assertContains(response, 'href="https://policies.google.com/privacy"')
        self.assertContains(response, 'href="https://www.youtube.com/t/terms"')
        self.assertContains(response, "agree to be bound by the")
        self.assertContains(response, "saved_shows")
        self.assertContains(response, "<code>near</code>")
        self.assertContains(response, "Gazetteer files")
        self.assertContains(response, "OpenStreetMap")

    def test_footer_link(self):
        for url in ("/", "/saved", "/submit-event", "/privacy"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, '<a href="/privacy">Privacy</a>')
                self.assertContains(response, 'href="https://www.openstreetmap.org/copyright"')
                self.assertContains(response, "© OpenStreetMap contributors")
