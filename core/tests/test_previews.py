"""preview-environments: which pull requests get a preview, what it is given, and what is removed"""

import os
import subprocess
from datetime import datetime, timedelta, timezone
from unittest import mock

from django.test import SimpleTestCase, TestCase

from core import preview_plan as plan
from core.preview_ops import LimitReached, Previews

NOW = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
IMAGES = "us-east1-docker.pkg.dev/stagehopper-previews/previews/site"


def pull(**fields):
    return {
        "state": "open", "merged": False, "sha": "abc123", "base": "main", "author": "natea",
        "head_repository": "natea/newenglandmusic", **fields,
    }


class WantsPreviewTestCase(SimpleTestCase):
    """Each pull request that changes code gets a preview"""

    def test_a_builds_pull_request(self):
        self.assertEqual(plan.wants_preview(pull(), ["core/views.py", "openspec/changes/x/tasks.md"]), (True, ""))

    def test_changes_to_specs_only(self):
        wanted, why = plan.wants_preview(pull(), ["openspec/changes/x/proposal.md", "docs/FABRO.md"])
        self.assertFalse(wanted)
        self.assertIn("specs or docs", why)

    def test_a_pull_request_from_a_fork(self):
        wanted, why = plan.wants_preview(pull(head_repository="someone/newenglandmusic"), ["core/views.py"])
        self.assertFalse(wanted)
        self.assertIn("forks", why)
        self.assertFalse(plan.wants_preview(pull(head_repository=None), ["core/views.py"])[0])

    def test_dependabot(self):
        wanted, why = plan.wants_preview(pull(author="dependabot[bot]"), ["requirements.txt"])
        self.assertFalse(wanted)
        self.assertIn("Dependabot", why)

    def test_another_base(self):
        self.assertFalse(plan.wants_preview(pull(base="change/x"), ["core/views.py"])[0])

    def test_names(self):
        self.assertEqual((plan.service_name(73), plan.branch_name(73)), ("preview-pr-73", "pr-73"))
        self.assertEqual([plan.preview_number(n) for n in ("preview-pr-73", "pr-73", "base", "pr-0", "pr-7x")], [73, 73, None, None, None])


class PreviewEnvTestCase(SimpleTestCase):
    """A preview never reaches the outside world"""

    def test_what_a_preview_is_given(self):
        tokens = iter(["key-1", "token-1"])
        env = plan.preview_env("postgres://branch", site_url="https://preview-pr-73.a.run.app", token=lambda n: next(tokens))
        self.assertEqual(
            env,
            {
                "DATABASE_URL": "postgres://branch",
                "DJANGO_SETTINGS_MODULE": "nycnoise.settings.preview",
                "DJANGO_SECRET_KEY": "key-1",
                "RC_DEVELOPER_INTERNAL_TOKEN": "token-1",
                "WEB_CONCURRENCY": "2",
                "PROD_INTERNAL_API_SERVER": "https://preview.invalid/",
                "PYINSTRUMENT_ENABLE": "false",
                "DEBUG_TOOLBAR_ENABLE": "false",
                "ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION": "False",
                "YOUTUBE_PREVIEWS": "true",
                "APPLE_MUSIC_PREVIEWS": "true",
                "SPOTIFY_CLIENT_ID": "preview-placeholder",
                "SPOTIFY_CLIENT_SECRET": "preview-placeholder",
                "APPLE_MUSIC_TEAM_ID": "preview-placeholder",
                "APPLE_MUSIC_KEY_ID": "preview-placeholder",
                "APPLE_MUSIC_PRIVATE_KEY": "preview-placeholder",
                "SITE_URL": "https://preview-pr-73.a.run.app",
            },
        )

    def test_new_secrets_each_time(self):
        first, second = plan.preview_env("postgres://branch"), plan.preview_env("postgres://branch")
        self.assertNotEqual(first["DJANGO_SECRET_KEY"], second["DJANGO_SECRET_KEY"])
        self.assertNotEqual(first["RC_DEVELOPER_INTERNAL_TOKEN"], first["DJANGO_SECRET_KEY"])
        self.assertGreaterEqual(len(first["RC_DEVELOPER_INTERNAL_TOKEN"]), 48)

    def test_no_working_key_and_no_jobs(self):
        env = plan.preview_env("postgres://branch")
        # nothing for mail, analytics, the sheet sync or the apis that fetch and match
        for name in (
            "DEFAULT_FROM_EMAIL", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "GOOGLE_SERVICE_ACCOUNT_JSON",
            "GOOGLE_PLACES_API_KEY", "YOUTUBE_API_KEY", "LASTFM_API_KEY", "ANTHROPIC_API_KEY", "TICKETMASTER_API_KEY",
            "EVENTBRITE_API_KEY", "SEATGEEK_CLIENT_ID", "POSTHOG_PROJECT_TOKEN", "GOATCOUNTER_CODE",
        ):
            self.assertNotIn(name, env)
        self.assertEqual({v for k, v in plan.PLAYER_SETTINGS.items() if "PREVIEWS" not in k}, {"preview-placeholder"})

    def test_the_database_is_the_previews_own(self):
        # Something saved on a preview: a preview is only ever given its branch's address
        env = plan.preview_env("postgres://pr-73-branch")
        self.assertEqual(env["DATABASE_URL"], "postgres://pr-73-branch")
        self.assertNotIn("PREVIEW_SOURCE_DATABASE_URL", env)


class PlayersTestCase(TestCase):
    def test_players_on_a_preview(self):
        from core import apple_music, spotify, youtube

        with mock.patch.dict(os.environ, plan.preview_env("postgres://branch")):
            self.assertTrue(spotify.credentials())
            self.assertTrue(apple_music.previews_enabled())
            self.assertTrue(youtube.previews_enabled())
            self.assertIsNone(youtube.api_key())


class SweepTestCase(SimpleTestCase):
    """A preview ends on merge or when idle"""

    def pulls(self, **overrides):
        base = {"state": "open", "merged": False, "pushed_at": NOW - timedelta(days=1)}
        return {**base, **overrides}

    def test_idle(self):
        pulls = {73: self.pulls(pushed_at=NOW - timedelta(days=7)), 74: self.pulls(pushed_at=NOW - timedelta(days=6, hours=23))}
        self.assertEqual(plan.to_sweep({73, 74}, pulls, NOW), [73])

    def test_merged_or_gone(self):
        pulls = {73: self.pulls(state="closed", merged=True)}
        self.assertEqual(plan.to_sweep({73, 99}, pulls, NOW), [73, 99])

    def test_closed_without_merging(self):
        pulls = {73: self.pulls(state="closed", pushed_at=NOW - timedelta(days=30))}
        self.assertEqual(plan.to_sweep({73}, pulls, NOW), [])

    def test_the_closed_one_pushed_to_longest_ago_makes_room(self):
        pulls = {
            70: self.pulls(state="closed", pushed_at=NOW - timedelta(days=3)),
            71: self.pulls(state="closed", pushed_at=NOW - timedelta(days=9)),
            72: self.pulls(pushed_at=NOW - timedelta(days=20)),
            73: self.pulls(state="closed", merged=True, pushed_at=NOW - timedelta(days=40)),
        }
        self.assertEqual(plan.to_evict({70, 71, 72, 73}, pulls), 71)
        self.assertIsNone(plan.to_evict({72}, pulls))


class GitHubPayloadTestCase(SimpleTestCase):
    def test_the_deployment_the_bridge_reads(self):
        self.assertEqual(
            plan.deployment_payload(73, "abc123"),
            {
                "ref": "abc123", "environment": "preview-pr-73", "description": "Preview of pull request #73",
                "required_contexts": [], "auto_merge": False, "transient_environment": True, "production_environment": False,
            },
        )
        status = plan.status_payload("https://preview-pr-73.a.run.app")
        self.assertEqual((status["state"], status["environment_url"]), ("success", "https://preview-pr-73.a.run.app"))
        self.assertEqual(plan.INACTIVE["state"], "inactive")


class FakeNeon:
    def __init__(self, names=("base",)):
        self.names = list(names)
        self.calls = []
        self.generation = {}

    def branches(self):
        return sorted(self.names)

    def create_branch(self, name):
        self.calls.append(("create_branch", name))
        self.names.append(name)
        self.generation[name] = self.generation.get(name, 0) + 1

    def delete_branch(self, name):
        self.calls.append(("delete_branch", name))
        if name in self.names:
            self.names.remove(name)

    def connection_url(self, name):
        return f"postgres://{name}-v{self.generation.get(name, 1)}"


class FakeGitHub:
    def __init__(self, pulls=None, files=None, pushed=None):
        self.pulls = pulls or {73: pull()}
        self.files = files or {}
        self.pushed = pushed or {}
        self.calls = []
        self.existing = {}

    def pull(self, number):
        return self.pulls.get(number)

    def pull_files(self, number):
        return self.files.get(number, ["core/views.py"])

    def pushed_at(self, sha):
        return self.pushed.get(sha, NOW - timedelta(days=1))

    def create_deployment(self, payload):
        self.calls.append(("create_deployment", payload))
        return 501

    def set_status(self, deployment, payload):
        self.calls.append(("set_status", deployment, payload["state"], payload.get("environment_url")))

    def deployments(self, environment):
        return self.existing.get(environment, [])


class FakeShell:
    def __init__(self, urls=None, fail_migrate=0):
        self.urls = dict(urls or {})
        self.calls = []
        self.fail_migrate = fail_migrate

    def build(self, image):
        self.calls.append(("build", image))

    def manage(self, image, env, *command, secret=None):
        self.calls.append(("manage", command[0], env["DATABASE_URL"], secret))
        if command[0] == "migrate" and self.fail_migrate:
            self.fail_migrate -= 1
            raise subprocess.CalledProcessError(1, "migrate")

    def service_url(self, service):
        return self.urls.get(service)

    def deploy(self, service, image, env, account):
        self.calls.append(("deploy", service, image, env["DATABASE_URL"], env.get("SITE_URL"), account))
        self.urls.setdefault(service, f"https://{service}-abc.a.run.app")

    def set_site_url(self, service, url):
        self.calls.append(("set_site_url", service, url))

    def services(self):
        return sorted(self.urls)

    def delete_service(self, service):
        self.calls.append(("delete_service", service))
        self.urls.pop(service, None)

    def delete_image(self, image):
        self.calls.append(("delete_image", image))


def previews(neon=None, github=None, shell=None):
    logs = []
    made = Previews(neon or FakeNeon(), github or FakeGitHub(), shell or FakeShell(), IMAGES, log=logs.append, now=lambda: NOW)
    made.logs = logs
    return made


class DeployTestCase(SimpleTestCase):
    """Each pull request that changes code gets a preview, on its own data"""

    def test_a_builds_pull_request(self):
        p = previews()
        url = p.deploy(73)
        self.assertEqual(url, "https://preview-pr-73-abc.a.run.app")
        self.assertEqual(p.neon.calls, [("create_branch", "pr-73")])
        self.assertEqual(
            p.shell.calls,
            [
                ("build", f"{IMAGES}:pr-73"),
                ("manage", "migrate", "postgres://pr-73-v1", None),
                ("manage", "set_preview_admin", "postgres://pr-73-v1", "PREVIEW_ADMIN_PASSWORD_HASH"),
                ("deploy", "preview-pr-73", f"{IMAGES}:pr-73", "postgres://pr-73-v1", None, "preview-runtime"),
                ("set_site_url", "preview-pr-73", url),
            ],
        )
        created, status = p.github.calls
        self.assertEqual((created[1]["environment"], created[1]["ref"]), ("preview-pr-73", "abc123"))
        self.assertEqual(status, ("set_status", 501, "success", url))

    def test_a_new_push(self):
        # the branch and the service exist: the same database, and one deploy that knows its address
        url = "https://preview-pr-73-abc.a.run.app"
        p = previews(neon=FakeNeon(["base", "pr-73"]), shell=FakeShell({"preview-pr-73": url}))
        p.deploy(73)
        self.assertEqual(p.neon.calls, [])
        self.assertIn(("deploy", "preview-pr-73", f"{IMAGES}:pr-73", "postgres://pr-73-v1", url, "preview-runtime"), p.shell.calls)
        self.assertNotIn("set_site_url", [c[0] for c in p.shell.calls])

    def test_a_pull_request_with_a_migration(self):
        p = previews()
        p.deploy(73)
        steps = [c[0] if c[0] != "manage" else c[1] for c in p.shell.calls]
        self.assertLess(steps.index("migrate"), steps.index("deploy"))
        self.assertTrue(all("pr-73" in c[2] for c in p.shell.calls if c[0] == "manage"))

    def test_a_migration_rewritten(self):
        p = previews(neon=FakeNeon(["base", "pr-73"]), shell=FakeShell(fail_migrate=1))
        p.neon.generation["pr-73"] = 1
        p.deploy(73)
        self.assertEqual(p.neon.calls, [("delete_branch", "pr-73"), ("create_branch", "pr-73")])
        self.assertIn(("manage", "migrate", "postgres://pr-73-v2", None), p.shell.calls)
        self.assertEqual([c[3] for c in p.shell.calls if c[0] == "deploy"], ["postgres://pr-73-v2"])
        self.assertTrue(any("loses what was saved" in line for line in p.logs))

    def test_migrations_that_fail_on_a_fresh_copy_too(self):
        p = previews(shell=FakeShell(fail_migrate=2))
        with self.assertRaises(subprocess.CalledProcessError):
            p.deploy(73)
        self.assertEqual(p.github.calls, [])

    def test_no_preview_for_specs_a_fork_or_dependabot(self):
        cases = {
            74: (pull(), ["openspec/changes/x/proposal.md"]),
            75: (pull(head_repository="someone/newenglandmusic"), ["core/views.py"]),
            76: (pull(author="dependabot[bot]"), ["requirements.txt"]),
        }
        github = FakeGitHub(pulls={n: p for n, (p, _) in cases.items()}, files={n: f for n, (_, f) in cases.items()})
        p = previews(github=github)
        for number in cases:
            self.assertEqual(p.deploy(number), "skipped")
            self.assertEqual(p.deploy(number, by_hand=True), "skipped")
        self.assertEqual((p.neon.calls, p.shell.calls, p.github.calls), ([], [], []))

    def test_reopened_and_rebuilt_by_hand(self):
        # after a sweep nothing is left of the preview: a reopen, or a run by hand, makes it again from the base
        for by_hand in (False, True):
            p = previews()
            p.deploy(73, by_hand=by_hand)
            self.assertEqual(p.neon.calls, [("create_branch", "pr-73")])
            self.assertEqual(p.github.calls[-1][2], "success")
        merged = previews(github=FakeGitHub(pulls={73: pull(state="closed", merged=True)}))
        self.assertEqual(merged.deploy(73, by_hand=True), "skipped")

    def full_house(self, pulls):
        neon = FakeNeon(["base", *[f"pr-{n}" for n in range(1, 10)]])
        return previews(neon=neon, github=FakeGitHub(pulls={**{n: pull(sha=f"sha{n}") for n in range(1, 10)}, **pulls, 73: pull()}))

    def test_every_slot_in_use(self):
        p = self.full_house({})
        with self.assertRaises(LimitReached) as raised:
            p.deploy(73)
        self.assertIn("limit of 9 previews", str(raised.exception))
        self.assertEqual(p.neon.calls, [])

    def test_a_slot_held_by_a_closed_pull_request(self):
        p = self.full_house({4: pull(state="closed", sha="sha4"), 6: pull(state="closed", sha="sha6")})
        p.github.pushed = {"sha4": NOW - timedelta(days=2), "sha6": NOW - timedelta(days=12)}
        p.deploy(73)
        self.assertEqual(p.neon.calls, [("delete_branch", "pr-6"), ("create_branch", "pr-73")])
        self.assertIn(("delete_service", "preview-pr-6"), p.shell.calls)


class RemoveTestCase(SimpleTestCase):
    """A preview ends on merge or when idle"""

    def test_merged(self):
        github = FakeGitHub(pulls={73: pull(state="closed", merged=True)})
        github.existing = {"preview-pr-73": [501, 502]}
        p = previews(neon=FakeNeon(["base", "pr-73"]), github=github, shell=FakeShell({"preview-pr-73": "https://x.a.run.app"}))
        self.assertEqual(p.closed(73), "removed")
        self.assertEqual(p.shell.calls, [("delete_service", "preview-pr-73"), ("delete_image", f"{IMAGES}:pr-73")])
        self.assertEqual(p.neon.calls, [("delete_branch", "pr-73")])
        self.assertEqual(github.calls, [("set_status", 501, "inactive", None), ("set_status", 502, "inactive", None)])

    def test_closed_without_merging(self):
        p = previews(neon=FakeNeon(["base", "pr-73"]), github=FakeGitHub(pulls={73: pull(state="closed")}))
        self.assertEqual(p.closed(73), "kept")
        self.assertEqual((p.neon.calls, p.shell.calls, p.github.calls), ([], [], []))

    def test_the_sweep(self):
        github = FakeGitHub(
            pulls={70: pull(sha="idle"), 71: pull(sha="fresh"), 72: pull(state="closed", sha="closed"), 73: pull(state="closed", merged=True)},
            pushed={"idle": NOW - timedelta(days=8), "fresh": NOW - timedelta(days=2), "closed": NOW - timedelta(days=30)},
        )
        github.existing = {"preview-pr-70": [7]}
        shell = FakeShell({f"preview-pr-{n}": "https://x.a.run.app" for n in (70, 71, 72, 73)})
        # 80 is a branch whose pull request no longer exists, left behind by a missed event
        p = previews(neon=FakeNeon(["base", "pr-70", "pr-71", "pr-72", "pr-73", "pr-80"]), github=github, shell=shell)
        self.assertEqual(p.sweep(), [70, 73, 80])
        self.assertEqual(p.neon.branches(), ["base", "pr-71", "pr-72"])
        self.assertIn(("set_status", 7, "inactive", None), github.calls)

    def test_sweeping_everything(self):
        p = previews(neon=FakeNeon(["base", "pr-71"]), shell=FakeShell({"preview-pr-72": "https://x.a.run.app"}))
        self.assertEqual(p.sweep(everything=True), [71, 72])
        self.assertEqual(p.neon.branches(), ["base"])
