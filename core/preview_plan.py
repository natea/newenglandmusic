"""
the decisions behind pull request previews (preview-environments): which pull requests get
one, what a preview is given, what GitHub is told, and which previews are removed. plain
functions, so the tests cover them; bin/preview acts on them through core/preview_ops.py.
nothing here imports django.
"""

import re
import secrets
from datetime import timedelta

REPOSITORY = "natea/newenglandmusic"
BASE_BRANCH = "main"
DEPENDABOT = "dependabot[bot]"
# neon's free plan has 10 branches in a project, and the cleaned copy is one of them
MAX_PREVIEWS = 9
IDLE = timedelta(days=7)
# a pull request touching only these gets no preview: there is no code to look at
IGNORED_PATHS = ("openspec/", "docs/")

PREVIEW_NAME = re.compile(r"^(?:preview-)?pr-([1-9][0-9]*)$")


def service_name(number):
    """the cloud run service, and the GitHub deployment environment"""
    return f"preview-pr-{number}"


def branch_name(number):
    """the neon branch, and the image's tag"""
    return f"pr-{number}"


def preview_number(name):
    """the pull request a service or branch name belongs to, or None"""
    found = PREVIEW_NAME.match(name or "")
    return int(found.group(1)) if found else None


def wants_preview(pull, files):
    """(whether the pull request gets a preview, why not)"""
    if pull.get("head_repository") != REPOSITORY:
        return False, "pull requests from forks get no preview"
    if pull.get("author") == DEPENDABOT:
        return False, "Dependabot's pull requests get no preview"
    if pull.get("base") != BASE_BRANCH:
        return False, f"only pull requests against {BASE_BRANCH} get a preview"
    if not any(not path.startswith(IGNORED_PATHS) for path in files):
        return False, "the pull request changes only specs or docs"
    return True, ""


# what the site's settings require to start (nycnoise/settings/base.py), with values that reach nothing
REQUIRED_PLACEHOLDERS = {
    "PROD_INTERNAL_API_SERVER": "https://preview.invalid/",
    "PYINSTRUMENT_ENABLE": "false",
    "DEBUG_TOOLBAR_ENABLE": "false",
    "ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION": "False",
}
# pages build their players from links stored in the database; these only switch them on.
# the credentials are placeholders: their presence is all the pages check, and no real key
# reaches a preview
PLAYER_SETTINGS = {
    "YOUTUBE_PREVIEWS": "true",
    "APPLE_MUSIC_PREVIEWS": "true",
    "SPOTIFY_CLIENT_ID": "preview-placeholder",
    "SPOTIFY_CLIENT_SECRET": "preview-placeholder",
    "APPLE_MUSIC_TEAM_ID": "preview-placeholder",
    "APPLE_MUSIC_KEY_ID": "preview-placeholder",
    "APPLE_MUSIC_PRIVATE_KEY": "preview-placeholder",
}


def preview_env(database_url, site_url=None, token=secrets.token_urlsafe):
    """exactly what a preview is given; the secret key and the export's token are new each time"""
    env = {
        "DATABASE_URL": database_url,
        "DJANGO_SETTINGS_MODULE": "nycnoise.settings.preview",
        "DJANGO_SECRET_KEY": token(48),
        "RC_DEVELOPER_INTERNAL_TOKEN": token(48),
        "WEB_CONCURRENCY": "2",
        **REQUIRED_PLACEHOLDERS,
        **PLAYER_SETTINGS,
    }
    if site_url:
        env["SITE_URL"] = site_url
    return env


def deployment_payload(number, sha):
    """the GitHub deployment a preview is reported as, which intentable's bridge reads"""
    return {
        "ref": sha,
        "environment": service_name(number),
        "description": f"Preview of pull request #{number}",
        # the tests may still be running, and nothing is to be merged into the branch
        "required_contexts": [],
        "auto_merge": False,
        "transient_environment": True,
        "production_environment": False,
    }


def status_payload(url):
    return {"state": "success", "environment_url": url, "description": "The preview is up"}


INACTIVE = {"state": "inactive", "description": "The preview was removed"}


def to_sweep(previews, pulls, now):
    """
    the previews the daily sweep removes: those whose pull request is gone or merged, and
    open pull requests' with no push for 7 days. `pulls` is {number: {"state", "merged",
    "pushed_at"}}, with no entry for a pull request that no longer exists. a pull request
    closed without merging keeps its preview until its slot is needed.
    """
    gone = []
    for number in sorted(previews):
        pull = pulls.get(number)
        if pull is None or pull["merged"]:
            gone.append(number)
        elif pull["state"] == "open" and now - pull["pushed_at"] >= IDLE:
            gone.append(number)
    return gone


def to_evict(previews, pulls):
    """when every slot is taken: the closed, unmerged pull request pushed to longest ago, or None"""
    closed = [n for n in previews if (pulls.get(n) or {}).get("state") == "closed" and not pulls[n]["merged"]]
    return min(closed, key=lambda n: (pulls[n]["pushed_at"], n)) if closed else None
