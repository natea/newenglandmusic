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

    def test_bandcamp_players(self):
        self.assertContains(self.client.get("/privacy"), "Players from Spotify, Apple Music, YouTube and Bandcamp")
        self.assertContains(self.client.get("/privacy"), 'href="https://bandcamp.com/privacy"')
        self.assertContains(self.client.get("/privacy"), "which may set its own cookies")

    def test_the_site_sets_no_policy_that_blocks_bandcamp_frames(self):
        # no content-security policy, frame-src or frame-ancestors is set: a Bandcamp frame needs none opened
        response = self.client.get("/")
        for header in ("Content-Security-Policy", "Content-Security-Policy-Report-Only"):
            self.assertNotIn(header, response)
        self.assertNotIn("frame-src", response.content.decode())

    def test_footer_link(self):
        for url in ("/", "/saved", "/submit-event", "/privacy"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, '<a href="/privacy">Privacy</a>')
                self.assertContains(response, 'href="https://www.openstreetmap.org/copyright"')
                self.assertContains(response, "© OpenStreetMap contributors")
