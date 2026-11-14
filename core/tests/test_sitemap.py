from core.models import Event
from core.tests.new_england_fixture import new_england_venue
from core.utils_datemath import get_current_new_york_datetime
from django.test import TestCase, override_settings
from django.utils import timezone


@override_settings(
    META_SITE_PROTOCOL="https", META_SITE_DOMAIN="newenglandmusic.example"
)
class SitemapTestCase(TestCase):
    def setUp(self):
        # the sitemap's months are new york's: utc has already turned the month on its last evening
        self.month = get_current_new_york_datetime().strftime("%Y-%m")
        Event.objects.create(venue=new_england_venue(), title="a show", starttime=timezone.now(), is_approved=True)

    def test_urls_use_the_site_address(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<loc>https://newenglandmusic.example/</loc>")
        self.assertContains(
            response, f"<loc>https://newenglandmusic.example/{self.month}/</loc>"
        )
        self.assertNotContains(response, "example.com")
