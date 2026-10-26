from core.models import Event
from django.test import TestCase, override_settings
from django.utils import timezone


@override_settings(
    META_SITE_PROTOCOL="https", META_SITE_DOMAIN="newenglandmusic.example"
)
class SitemapTestCase(TestCase):
    def setUp(self):
        self.month = timezone.now().strftime("%Y-%m")
        Event.objects.create(title="a show", starttime=timezone.now(), is_approved=True)

    def test_urls_use_the_site_address(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<loc>https://newenglandmusic.example/</loc>")
        self.assertContains(
            response, f"<loc>https://newenglandmusic.example/{self.month}/</loc>"
        )
        self.assertNotContains(response, "example.com")
