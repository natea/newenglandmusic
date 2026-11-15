from django.test import TestCase, override_settings


@override_settings(SITE_NAME="StageHopper")
class IndexPageTestCase(TestCase):
    def test_index_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/index.html")
        self.assertContains(response, "<h1>StageHopper</h1>")
        self.assertNotContains(response, "always incomplete")
