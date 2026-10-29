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
    "manage.py sync_venues_from_gsheets",
    "manage.py lookup_venue_places",
    "manage.py lookup_venue_places --refresh-stale",
    "manage.py fetch_events --all",
    "manage.py match_spotify_artists --limit 500",
    "manage.py match_apple_music_artists --limit 1000",
    "manage.py resolve_artists_with_lastfm --limit 300",
    "manage.py match_youtube_artists --limit 90",
]
WEEKLY = [
    "manage.py check_event_sources --workers 8",
    "manage.py match_ticketmaster_venues",
    "manage.py match_eventbrite_organizers",
    "manage.py match_seatgeek_venues",
    "manage.py lookup_venue_neighborhoods",
]


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

    def test_memory_pools_are_capped(self):
        # threads on linux otherwise run the jobs out of memory
        self.run_job("weekly.sh")
        self.assertEqual(self.arenas, "2")

    def test_output_is_unbuffered(self):
        # so the host's log shows each command's report as it runs
        for script in ("daily.sh", "weekly.sh"):
            self.run_job(script)
            self.assertEqual(self.unbuffered, "1", script)

    def test_weekly_run(self):
        result, calls = self.run_job("weekly.sh")
        self.assertEqual(calls, WEEKLY)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_sheet_sync_fails(self):
        result, calls = self.run_job("daily.sh", fail_step=DAILY[0])
        # the later steps still run
        self.assertEqual(calls, DAILY)
        self.assertEqual(result.returncode, 1)
        self.assertIn("=== 1 step(s) failed:\n  python manage.py sync_venues_from_gsheets", result.stdout)

    def test_scripts_name_real_commands(self):
        commands = get_commands()
        for script in ("daily.sh", "weekly.sh"):
            named = re.findall(r"^step python manage\.py (\w+)", (BIN / script).read_text(), re.M)
            self.assertTrue(named, script)
            for command in named:
                self.assertIn(command, commands, f"{script}: {command}")

    def test_scripts_are_executable(self):
        for script in ("daily.sh", "weekly.sh", "build-job.sh"):
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
                "YOUTUBE_PREVIEWS",
                "LASTFM_API_KEY",
            },
        )
        self.assertEqual(
            self.keys_from_web(weekly),
            {"DJANGO_SECRET_KEY", "TICKETMASTER_API_KEY", "EVENTBRITE_API_KEY", "SEATGEEK_CLIENT_ID", "API_CONTACT_EMAIL"},
        )
        for job in (daily, weekly):
            database = next(var for var in job["envVars"] if var["key"] == "DATABASE_URL")
            self.assertEqual(database["fromDatabase"]["name"], "newenglandmusic")
            self.assertEqual(job["autoDeployTrigger"], "checksPass")

    def test_jobs_dont_migrate(self):
        for name in ("newenglandmusic-daily", "newenglandmusic-weekly"):
            build = (ROOT / self.services[name]["buildCommand"]).read_text()
            self.assertNotIn("migrate", re.sub(r"#.*", "", build), name)
