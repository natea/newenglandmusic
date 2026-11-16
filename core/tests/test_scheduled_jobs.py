import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

import yaml
from django.core.management import get_commands
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[2]
BIN = ROOT / "bin"

# stands in for python: records each call, and fails the one matching $FAIL_STEP
STUB_PYTHON = """#!/usr/bin/env bash
echo "$*" >> "$CALLS"
echo "$MALLOC_ARENA_MAX" > "$CALLS.arenas"
echo "$PYTHONUNBUFFERED" > "$CALLS.unbuffered"
if [ -n "$FAIL_STEP" ] && [ "$*" = "$FAIL_STEP" ]; then
  exit 3
fi
"""

DAILY = [
    "manage.py lookup_venue_places",
    "manage.py lookup_venue_places --refresh-stale",
    "manage.py fetch_events --all",
    "manage.py match_spotify_artists --limit 500",
    "manage.py match_apple_music_artists --limit 1000",
    "manage.py resolve_artists_with_lastfm --limit 300",
    "manage.py match_youtube_artists --limit 90",
    "manage.py enrich_artists_from_musicbrainz --limit 100",
]
WEEKLY = [
    "manage.py check_event_sources --workers 8",
    "manage.py match_ticketmaster_venues",
    "manage.py match_eventbrite_organizers",
    "manage.py match_seatgeek_venues",
    "manage.py lookup_venue_neighborhoods",
]
DIGEST = ["manage.py send_weekly_digests"]


class JobScriptsTestCase(SimpleTestCase):
    def run_job(self, script, fail_step=""):
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "python"
            stub.write_text(STUB_PYTHON)
            stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
            calls = Path(tmp) / "calls"
            calls.touch()
            env = {
                **os.environ,
                "PATH": f"{tmp}:{os.environ['PATH']}",
                "CALLS": str(calls),
                "FAIL_STEP": fail_step,
            }
            result = subprocess.run(
                ["bash", str(BIN / script)], env=env, capture_output=True, text=True, timeout=30
            )
            self.arenas = Path(f"{calls}.arenas").read_text().strip() if Path(f"{calls}.arenas").exists() else None
            self.unbuffered = Path(f"{calls}.unbuffered").read_text().strip() if Path(f"{calls}.unbuffered").exists() else None
            return result, calls.read_text().splitlines()

    def test_daily_run(self):
        result, calls = self.run_job("daily.sh")
        self.assertEqual(calls, DAILY)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("=== every step succeeded", result.stdout)

    def test_enrichment_fails(self):
        result, calls = self.run_job("daily.sh", fail_step=DAILY[-1])
        # it runs last, so every step before it has already run
        self.assertEqual(calls, DAILY)
        self.assertEqual(result.returncode, 1)
        self.assertIn("=== 1 step(s) failed:\n  python manage.py enrich_artists_from_musicbrainz --limit 100", result.stdout)

    def test_memory_pools_are_capped(self):
        # threads on linux otherwise run the jobs out of memory
        self.run_job("weekly.sh")
        self.assertEqual(self.arenas, "2")

    def test_output_is_unbuffered(self):
        # so the host's log shows each command's report as it runs
        for script in ("daily.sh", "weekly.sh", "digest.sh"):
            self.run_job(script)
            self.assertEqual(self.unbuffered, "1", script)

    def test_weekly_run(self):
        result, calls = self.run_job("weekly.sh")
        self.assertEqual(calls, WEEKLY)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_the_bandcamp_finder_and_link_hubs_arent_scheduled(self):
        # bandcamp challenges requests from render's servers, and the hubs' robots.txt forbids
        # reading them, so both run by hand
        for script in ("daily.sh", "weekly.sh", "digest.sh"):
            _, calls = self.run_job(script)
            for command in ("manage.py find_bandcamp_embeds", "manage.py read_artist_link_hubs"):
                self.assertNotIn(command, calls, script)

    def test_digest_run(self):
        result, calls = self.run_job("digest.sh")
        self.assertEqual(calls, DIGEST)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_failed_digest_fails_the_job(self):
        result, calls = self.run_job("digest.sh", fail_step=DIGEST[0])
        self.assertEqual(result.returncode, 1)
        self.assertIn("=== 1 step(s) failed:\n  python manage.py send_weekly_digests", result.stdout)

    def test_digest_script_sources_the_shared_steps(self):
        self.assertIn('source "$(dirname "$0")/steps.sh"', (BIN / "digest.sh").read_text())

    def test_places_lookup_fails(self):
        result, calls = self.run_job("daily.sh", fail_step=DAILY[0])
        # the later steps still run
        self.assertEqual(calls, DAILY)
        self.assertEqual(result.returncode, 1)
        self.assertIn("=== 1 step(s) failed:\n  python manage.py lookup_venue_places\n", result.stdout)

    def test_the_sheet_sync_isnt_in_the_daily_job(self):
        result, calls = self.run_job("daily.sh")
        self.assertNotIn("manage.py sync_venues_from_gsheets", calls)
        self.assertEqual(len(calls), 8)

    def test_scripts_name_real_commands(self):
        commands = get_commands()
        for script in ("daily.sh", "weekly.sh", "digest.sh"):
            named = re.findall(r"^step python manage\.py (\w+)", (BIN / script).read_text(), re.M)
            self.assertTrue(named, script)
            for command in named:
                self.assertIn(command, commands, f"{script}: {command}")

    def test_scripts_are_executable(self):
        for script in ("daily.sh", "weekly.sh", "digest.sh", "build-job.sh"):
            self.assertTrue(os.access(BIN / script, os.X_OK), script)


class RenderConfigurationTestCase(SimpleTestCase):
    def setUp(self):
        services = yaml.safe_load((ROOT / "render.yaml").read_text())["services"]
        self.services = {service["name"]: service for service in services}

    def keys_from_web(self, job):
        return {
            var["key"]
            for var in job["envVars"]
            if var.get("fromService") == {"type": "web", "name": "newenglandmusic", "envVarKey": var["key"]}
        }

    def test_configuration(self):
        daily = self.services["newenglandmusic-daily"]
        weekly = self.services["newenglandmusic-weekly"]
        self.assertEqual((daily["type"], daily["schedule"], daily["startCommand"]), ("cron", "0 10 * * *", "./bin/daily.sh"))
        # sundays, three hours before that day's daily run
        self.assertEqual((weekly["type"], weekly["schedule"], weekly["startCommand"]), ("cron", "0 7 * * 0", "./bin/weekly.sh"))
        self.assertEqual(
            self.keys_from_web(daily),
            {
                "DJANGO_SECRET_KEY",
                "GOOGLE_SERVICE_ACCOUNT_JSON",
                "GOOGLE_PLACES_API_KEY",
                "ANTHROPIC_API_KEY",
                "TICKETMASTER_API_KEY",
                "EVENTBRITE_API_KEY",
                "SEATGEEK_CLIENT_ID",
                # spotify matching, and new events rendering their play buttons
                "SPOTIFY_CLIENT_ID",
                "SPOTIFY_CLIENT_SECRET",
                "APPLE_MUSIC_TEAM_ID",
                "APPLE_MUSIC_KEY_ID",
                "APPLE_MUSIC_PRIVATE_KEY",
                "APPLE_MUSIC_PREVIEWS",
                "YOUTUBE_API_KEY",
                "API_CONTACT_EMAIL",
                # the contact address in the api clients' user agent
                "SITE_URL",
                "YOUTUBE_PREVIEWS",
                "LASTFM_API_KEY",
            },
        )
        self.assertEqual(
            self.keys_from_web(weekly),
            {"DJANGO_SECRET_KEY", "TICKETMASTER_API_KEY", "EVENTBRITE_API_KEY", "SEATGEEK_CLIENT_ID", "API_CONTACT_EMAIL", "SITE_URL"},
        )
        digest = self.services["newenglandmusic-digest"]
        # thursdays at 13:00 utc, a script that reports failure like the others
        self.assertEqual((digest["type"], digest["schedule"], digest["startCommand"]), ("cron", "0 13 * * 4", "./bin/digest.sh"))
        self.assertEqual(
            self.keys_from_web(digest),
            {"DJANGO_SECRET_KEY", "SITE_URL", "DEFAULT_FROM_EMAIL", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"},
        )
        for job in (daily, weekly, digest):
            database = next(var for var in job["envVars"] if var["key"] == "DATABASE_URL")
            self.assertEqual(database["fromDatabase"]["name"], "newenglandmusic")
            self.assertEqual(job["autoDeployTrigger"], "checksPass")

    def test_jobs_dont_migrate(self):
        for name in ("newenglandmusic-daily", "newenglandmusic-weekly", "newenglandmusic-digest"):
            build = (ROOT / self.services[name]["buildCommand"]).read_text()
            self.assertNotIn("migrate", re.sub(r"#.*", "", build), name)

    def test_the_web_service_declares_what_the_digest_job_copies(self):
        web = {var["key"]: var for var in self.services["newenglandmusic"]["envVars"]}
        for key in ("SITE_URL", "DEFAULT_FROM_EMAIL", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
            self.assertIs(web[key].get("sync"), False, key)
        digest = self.services["newenglandmusic-digest"]
        # the settings read this one without a default
        values = {var["key"]: var.get("value") for var in digest["envVars"]}
        self.assertEqual(values["ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION"], "False")
        self.assertEqual(values["DJANGO_SETTINGS_MODULE"], "nycnoise.settings.prod")
