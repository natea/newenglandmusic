"""site-identity: the site's name and tagline, its address and redirects, the health check,
and the terms and privacy pages (openspec change rename-to-stagehopper)"""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from core.models import Event, Venue
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# reads the base settings in a fresh interpreter, with none of the site's name settings in
# the environment, so the defaults are tested whatever a developer's .env says
READ_DEFAULTS = """
import json
from nycnoise.settings import base
print(json.dumps({
    "site_name": base.SITE_NAME,
    "site_tagline": base.SITE_TAGLINE,
    "uid_domain": base.UID_DOMAIN,
    "canonical_host": base.CANONICAL_HOST,
}))
"""
NAME_SETTINGS = ("SITE_NAME", "SITE_TAGLINE", "UID_DOMAIN", "CANONICAL_HOST")


def default_settings():
    env = {key: value for key, value in os.environ.items() if key not in NAME_SETTINGS}
    result = subprocess.run(
        [sys.executable, "-c", READ_DEFAULTS], capture_output=True, text=True, check=True, cwd=PROJECT_ROOT, env=env
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


class DefaultsTestCase(SimpleTestCase):
    """the defaults the scenarios' "unset" cases rely on"""

    def test_the_defaults(self):
        self.assertEqual(
            default_settings(),
            {
                "site_name": "StageHopper",
                "site_tagline": "Live music across New England",
                "uid_domain": "stagehopper",
                "canonical_host": "",
            },
        )


@override_settings(SITE_NAME="StageHopper", SITE_TAGLINE="Live music across New England")
class TheSiteIsNamedTestCase(TestCase):
    """The site is named StageHopper; the masthead carries a tagline"""

    def test_the_masthead_and_title(self):
        response = self.client.get("/")
        self.assertContains(response, "<h1>StageHopper</h1>")
        self.assertContains(response, "<title>StageHopper</title>")
        self.assertContains(response, '<meta property="og:title" content="StageHopper">')

    def test_the_default_tagline(self):
        response = self.client.get("/")
        self.assertContains(response, '<h1>StageHopper</h1></a>\n                      <p class="tagline">Live music across New England</p>')

    @override_settings(SITE_TAGLINE=" ")
    def test_no_tagline(self):
        response = self.client.get("/")
        self.assertContains(response, "<h1>StageHopper</h1>")
        self.assertNotContains(response, 'class="tagline"')

    def test_an_events_calendar_entry(self):
        venue = Venue.objects.create(name=f"venue {uuid.uuid4()}", city_town="Boston", state="MA")
        event = Event.objects.create(title="Dummy Ache", starttime=timezone.now(), venue=venue)
        content = self.client.get(f"/event/{event.pk}/ics").content.decode()
        self.assertIn("SUMMARY:Dummy Ache [StageHopper]", content)


@override_settings(SITE_NAME="Boston Shows")
class ANameFromTheSettingTestCase(TestCase):
    def test_a_name_from_the_setting(self):
        self.assertContains(self.client.get("/"), "<h1>Boston Shows</h1>")
        admin_user = get_user_model().objects.create_superuser("editor", "editor@example.org", "x")
        self.client.force_login(admin_user)
        self.assertContains(self.client.get("/admin/"), "Boston Shows")
        venue = Venue.objects.create(name=f"venue {uuid.uuid4()}", city_town="Boston", state="MA")
        event = Event.objects.create(title="Dummy Ache", starttime=timezone.now(), venue=venue)
        self.assertIn("SUMMARY:Dummy Ache [Boston Shows]", self.client.get(f"/event/{event.pk}/ics").content.decode())


ONRENDER = "newenglandmusic.onrender.com"
HOSTS = ["stagehopper.app", "www.stagehopper.app", ONRENDER, "testserver", "127.0.0.1"]
PRODUCTION = override_settings(CANONICAL_HOST="stagehopper.app", SITE_URL="https://stagehopper.app", ALLOWED_HOSTS=HOSTS)


class TheSitesAddressTestCase(SimpleTestCase):
    """The site's address comes from SITE_URL"""

    def test_productions_hosts(self):
        from core.tests.test_prod_settings import ProdSettingsTestCase

        prod = ProdSettingsTestCase().prod_settings(allowed_hosts="", RENDER_EXTERNAL_HOSTNAME=ONRENDER)
        for host in ("stagehopper.app", "www.stagehopper.app", ONRENDER):
            self.assertIn(host, prod["allowed_hosts"])

    @override_settings(SITE_URL="https://stagehopper.app")
    def test_the_api_clients_contact_address(self):
        from core.user_agent import user_agent

        self.assertIn("https://stagehopper.app", user_agent())
        self.assertNotIn("onrender.com", user_agent())

    def test_the_scheduled_jobs_get_the_address(self):
        import yaml

        services = yaml.safe_load((PROJECT_ROOT / "render.yaml").read_text())["services"]
        jobs = [s for s in services if s["type"] == "cron"]
        self.assertEqual(len(jobs), 2)
        for job in jobs:
            site_url = next(v for v in job["envVars"] if v["key"] == "SITE_URL")
            self.assertEqual(site_url["fromService"], {"type": "web", "name": "newenglandmusic", "envVarKey": "SITE_URL"})


@PRODUCTION
class OtherAddressesRedirectTestCase(TestCase):
    """Other addresses redirect to the site's address; a redirected form keeps its method"""

    def test_the_old_address(self):
        response = self.client.get("/bands", {"state": "VT"}, HTTP_HOST=ONRENDER)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://stagehopper.app/bands?state=VT")

    def test_the_www_address(self):
        response = self.client.get("/", HTTP_HOST="www.stagehopper.app")
        self.assertEqual((response.status_code, response["Location"]), (301, "https://stagehopper.app/"))

    def test_a_calendar_feed_on_the_old_address(self):
        response = self.client.get("/calendar.ics", {"state": "VT"}, HTTP_HOST=ONRENDER)
        self.assertEqual((response.status_code, response["Location"]), (301, "https://stagehopper.app/calendar.ics?state=VT"))

    def test_a_form_posted_to_the_old_address(self):
        response = self.client.post("/submit-event", {"title": "x"}, HTTP_HOST=ONRENDER)
        self.assertEqual((response.status_code, response["Location"]), (308, "https://stagehopper.app/submit-event"))

    def test_the_target_never_comes_from_the_host_header(self):
        response = self.client.get("/", HTTP_HOST="127.0.0.1")
        self.assertEqual(response["Location"], "https://stagehopper.app/")


class NoCanonicalHostTestCase(TestCase):
    @override_settings(CANONICAL_HOST="", SITE_URL="http://localhost:8001", ALLOWED_HOSTS=HOSTS)
    def test_no_canonical_host(self):
        self.assertEqual(self.client.get("/", HTTP_HOST="127.0.0.1:8001").status_code, 200)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_the_default_settings_redirect_nothing(self):
        self.assertEqual(self.client.get("/").status_code, 200)


@PRODUCTION
class TheHealthCheckTestCase(TestCase):
    def test_the_health_check(self):
        response = self.client.get("/health", HTTP_HOST=ONRENDER)
        self.assertEqual((response.status_code, response.content), (200, b"ok"))


@PRODUCTION
class TheLandingPagesOldPathsTestCase(TestCase):
    """The landing page's old paths go to its new address"""

    def test_the_landing_pages_privacy_policy(self):
        response = self.client.get("/privacy.html", HTTP_HOST="stagehopper.app")
        self.assertEqual((response.status_code, response["Location"]), (301, "https://info.stagehopper.app/privacy.html"))

    def test_a_landing_map(self):
        response = self.client.get("/events_map_boston.html", HTTP_HOST="stagehopper.app")
        self.assertEqual(response["Location"], "https://info.stagehopper.app/events_map_boston.html")

    def test_its_data_images_and_folders(self):
        for path in ("/nyc.geojson", "/boston_gallery.json", "/og_nyc.png", "/boston/thumb.jpg"):
            self.assertEqual(self.client.get(path, HTTP_HOST="stagehopper.app")["Location"], f"https://info.stagehopper.app{path}", path)

    def test_the_sites_own_privacy_page(self):
        self.assertEqual(self.client.get("/privacy", HTTP_HOST="stagehopper.app").status_code, 200)


@override_settings(SITE_NAME="StageHopper", CONTACT_EMAIL="hello@example.org")
class TermsAndPrivacyTestCase(TestCase):
    """The site has a terms page; the privacy page says how email addresses are handled"""

    def test_the_footer(self):
        self.assertContains(self.client.get("/"), '<a href="/privacy">Privacy</a> | <a href="/terms">Terms</a>')

    def test_the_terms_page(self):
        response = self.client.get("/terms")
        self.assertContains(response, "StageHopper is a free calendar")
        self.assertContains(response, "Jazkarta, Inc. d/b/a StageHopper")
        self.assertContains(response, 'href="mailto:hello@example.org"')

    def test_email_addresses_on_the_privacy_page(self):
        response = self.client.get("/privacy")
        self.assertContains(response, "<h2>Your email address</h2>")
        self.assertContains(response, "If you submit an event")
        self.assertContains(response, "If you sign up for email")
        self.assertContains(response, "To have yours removed")

    @override_settings(SITE_NAME="Boston Shows")
    def test_both_pages_follow_the_setting(self):
        for path in ("/terms", "/privacy"):
            page = self.client.get(path).content.decode()
            self.assertIn("Boston Shows", page, path)
            # the operator's name stays; the site's own name follows the setting
            self.assertNotIn("<p>StageHopper ", page, path)
