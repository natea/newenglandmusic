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
