from core.site_record import site_domain, sync_site_record
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.test import RequestFactory, TestCase, override_settings


class SiteRecordTestCase(TestCase):
    """the sites record is this site's own address, never example.com"""

    def setUp(self):
        # get_current_site caches the record per process, across tests
        Site.objects.clear_cache()
        self.addCleanup(Site.objects.clear_cache)

    def test_made_by_migrate_from_the_settings(self):
        site = Site.objects.get_current()
        self.assertNotEqual(site.domain, "example.com")
        self.assertEqual(site.domain, site_domain())

    @override_settings(SITE_URL="https://newenglandmusic.org/", SITE_NAME="New England Music")
    def test_follows_a_new_domain(self):
        sync_site_record()
        site = get_current_site(RequestFactory().get("/"))
        self.assertEqual((site.domain, site.name), ("newenglandmusic.org", "New England Music"))

    @override_settings(SITE_URL="http://localhost:8001")
    def test_keeps_a_port(self):
        self.assertEqual(site_domain(), "localhost:8001")

    def test_read_only_in_the_admin(self):
        self.client.force_login(User.objects.create_superuser("admin", password="pw"))
        site = Site.objects.get_current()
        self.assertEqual(self.client.get("/admin/sites/site/").status_code, 200)
        self.assertEqual(self.client.get("/admin/sites/site/add/").status_code, 403)
        self.client.post(f"/admin/sites/site/{site.pk}/change/", {"domain": "example.com", "name": "x"})
        self.assertEqual(Site.objects.get(pk=site.pk).domain, site_domain())
