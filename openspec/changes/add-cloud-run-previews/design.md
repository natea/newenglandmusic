## Context

The live site runs on Render:
- a web service built by `bin/build.sh`, which installs, compiles the CSS, collects static files and migrates;
- a Postgres 17 database of about 20 MB, reachable from outside through its External Database URL (`PRODUCTION.md`);
- three cron jobs.

Static files are served by WhiteNoise. GitHub Actions (`django.yml`) runs the tests on pull requests and on pushes to `main`, and Render deploys `main` only once its checks pass (`autoDeployTrigger: checksPass`).

`nycnoise/settings/base.py` reads five variables at import and fails without them: `DJANGO_SECRET_KEY`, `RC_DEVELOPER_INTERNAL_TOKEN`, `PROD_INTERNAL_API_SERVER`, `PYINSTRUMENT_ENABLE` and `ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION`. It also sets `conn_max_age=600`.

`/internal-api/db` (inherited from nycnoise) returns every event, venue and page to anyone sending the token `RC_DEVELOPER_INTERNAL_TOKEN`.

Mail goes out through `core/digest_mail.py`, which refuses to send (`MailNotReady`) unless `DEFAULT_FROM_EMAIL` is a real sender. Code that uses Spotify, Apple Music, YouTube, Last.fm, Places or the sheet sync skips quietly when its keys are missing. The listing's play buttons are stored in each event's saved HTML. Event pages and the discovery deck build their players at request time from those settings.

People's data is in:
- `Subscriber`, `EmailSubscriber`, `SignInCode`, `DigestChoice` and `MailRequest`, which hold only people's data;
- `django_session`;
- `django_admin_log`, whose entries name the subscribers that admins changed, by email;
- Django's users, with usernames, names, emails and password hashes;
- `Event.user_submission_email`;
- `JobRun.output` and `JobRun.error`, which hold production tracebacks. `VenueFetchStatus` points at `JobRun`, so the rows must stay.

The fork's `Dockerfile` is upstream's: Python 3.12.1, a `.env` build secret, and `bin/serve.sh` on port 8000.

Vendor behaviour this design relies on is from the vendors' documentation, not yet checked on our accounts (task 1.1):
- Cloud Run scales a service to zero, and its monthly free allowance applies in some regions, `us-east1` among them.
- A Neon branch is a copy-on-write child of its parent, and a branch with children can't be deleted.
- A Neon compute suspends after 5 idle minutes.
- Neon's free plan allows 10 branches in a project.

## Goals / Non-Goals

**Goals:**
- uncleaned data exists only on the nightly job's runner, for the length of the job;
- pull request code, which the build agent writes, can reach no personal data and no production credential;
- a preview costs close to nothing while nobody looks at it;
- every decision the workflows make is in code the site's tests cover.

**Non-Goals:**
- the issue side, which intentable's bridge has;
- refreshing a preview's data while it lives.

## Decisions

**Clean on the runner, load only clean data.** `preview-base.yml` runs nightly on `main`, with a Postgres 17 service container, as `django.yml` has. It:
1. checks the source role can't write (`has_table_privilege(..., 'INSERT')` on a core table), and refuses if it can;
2. runs `pg_dump` 17, from the `postgres:17` image since the runner's client is older, from `PREVIEW_SOURCE_DATABASE_URL` into the service container, with `--exclude-table-data` for the left-out tables;
3. runs `migrate` and `scrub_preview_data` against the container;
4. dumps the cleaned container and restores it into Neon's one long-lived `base` branch with `pg_restore --clean --if-exists --single-transaction`.

A failure at any step leaves `base` as it was. There is no second base branch and no swap. A swap would need deleting the old base, which Neon refuses while previews branch from it, and it would use up branches. Existing preview branches keep the data they branched with.

The alternative was restoring into Neon and scrubbing there. That would put uncleaned data where pull request code holds an API key.

**Every table is classified.** `core/preview_data.py` lists each table as one of:
- `COPIED`;
- `LEFT_OUT`, whose data is never dumped: the five people-only tables, `django_session`, `django_admin_log`, `auth_user` and its group and permission link tables;
- `CLEANED`, with what is done: `core_event.user_submission_email` emptied, and `core_jobrun.output` and `error` emptied.

A test compares the lists with the database's tables and fails on one that is missing. That is broader than looking for `EmailField`, which would miss `MailRequest.address` and the admin log. The dump's exclusions and the scrub are both built from these lists.

**The scrub.** `scrub_preview_data`:
- refuses unless the settings module is `nycnoise.settings.preview` and the database's host is local or Neon's (`*.neon.tech`), so it can't run against Render;
- empties the `CLEANED` fields, and deletes any row left in a `LEFT_OUT` table.

A separate command, `set_preview_admin`, creates or updates `preview-admin` from `PREVIEW_ADMIN_PASSWORD`. It runs per pull request, on the preview's branch, so the base holds no account at all.

**Secrets by reach.**
- `PREVIEW_SOURCE_DATABASE_URL` is a secret of a GitHub environment, `preview-base`, whose deployment branch is `main` only. Only `preview-base.yml` names that environment. A pull request's workflow can't read it, even if the pull request rewrites the workflow file.
- The pull request workflow gets `NEON_API_KEY` and `PREVIEW_ADMIN_PASSWORD`, and signs in to Google without a key (Workload Identity Federation, limited to this repository). Pull request code can therefore reach the Neon project and the previews' Google project. Both hold only cleaned data and previews, so the Neon account is used for nothing else.
- The Cloud Run services run as a service account with no roles, not the project's default one.
- The workflows carry `if: github.repository == 'natea/newenglandmusic'`, as `spek.yml` does.

**The pull request workflow.** `preview.yml` runs on:
- `pull_request` (`opened`, `synchronize`, `reopened`, `closed`), for pull requests whose head is in this repository and whose author isn't Dependabot;
- `workflow_dispatch` with a pull request number, to rebuild by hand.

One `concurrency` group per pull request stops two runs racing. `bin/preview-plan` decides from the changed files whether the pull request gets a preview, so a spec-only pull request that later gains code gets one on that push.

To deploy, it:
1. builds the image and pushes it to Artifact Registry, tagged `pr-<n>`, so each pull request keeps one image;
2. creates the Neon branch `pr-<n>` from `base` if it doesn't exist, failing with "the limit of 9 previews is reached" when Neon refuses;
3. runs `migrate` from the image against the branch. On failure it deletes the branch, makes it again from `base` and migrates once more;
4. runs `set_preview_admin`;
5. deploys `preview-pr-<n>` with `--min-instances 0 --max-instances 1 --allow-unauthenticated` and the variables below;
6. reads the service's address (`status.url`), and sets it as the service's `SITE_URL`;
7. creates a GitHub deployment of `preview-pr-<n>` and sets its status to `success` with `environment_url`.

For the deployment in step 7:
- `required_contexts: []`, so the tests still running don't block it;
- `auto_merge: false`;
- `transient_environment: true`;
- the workflow has `deployments: write` and `id-token: write`.

On `closed` with `merged`, it deletes the service, the branch and the image, and sets every deployment of the environment to `inactive`. On `closed` without a merge it does nothing (open question 1).

**What a preview is given.** `bin/preview-plan env` prints the exact list, which a test pins:
- `DATABASE_URL`, the branch's;
- `DJANGO_SETTINGS_MODULE=nycnoise.settings.preview`;
- `DJANGO_SECRET_KEY` and `RC_DEVELOPER_INTERNAL_TOKEN`, each random per deploy;
- `PROD_INTERNAL_API_SERVER=https://preview.invalid/`, `PYINSTRUMENT_ENABLE=false`, `DEBUG_TOOLBAR_ENABLE=false` and `ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION=False`, which `base.py` requires;
- `WEB_CONCURRENCY=2`;
- the player settings Nate allows (open question 5).

The image's build step passes placeholders for the five required variables, with no secret.

**Preview settings.** `nycnoise/settings/preview.py` extends `prod`:
- `ALLOWED_HOSTS = [".run.app"]`, since the address isn't known before the first deploy. `prod.py` already handles https behind a proxy;
- `DEFAULT_FROM_EMAIL` empty, so `MailNotReady` refuses every email;
- `CONN_MAX_AGE = 0`, since Neon suspends an idle database and a kept connection would fail;
- `PREVIEW = True`, which makes `/internal-api/db` answer 404;
- a middleware, placed above WhiteNoise, that adds `X-Robots-Tag: noindex, nofollow` to every response, static files included.

**The image.** The `Dockerfile` becomes `python:3.11.14-slim`, installs `requirements.txt`, runs `compilescss` and `collectstatic`, and starts gunicorn as `render.yaml`'s `startCommand` does. Gunicorn binds `$PORT` itself. A `.dockerignore` keeps `.env` and `.git` out. The image is built only in `preview.yml`, so nothing is added to `django.yml` and `main`'s checks are as before. `bin/serve.sh` stays for local use.

**Sweep.** After the nightly copy, `bin/preview-sweep` lists the `preview-pr-*` services and `pr-*` branches. It deletes each whose pull request is merged, is gone, or has had no push for 7 days, with its image, and sets the environment's deployments to `inactive`, so the bridge never reads a dead address as live.

**Testing, and how the outside services are stood in for.** The decisions live in `core/preview_plan.py`, as plain functions with unit tests:
- which pull requests get a preview;
- the variable list;
- the deployment's payload;
- what the sweep removes.

The `bin/preview-*` scripts are thin. They call Neon's and GitHub's APIs through one small client and `gcloud` through one function. Tests replace both with fakes that record the calls, so each scenario of the workflow has an automated test of its decisions and calls. Tests also read the two workflow files, as the scheduled-jobs tests read `render.yaml`, for their triggers, the environment, permissions, concurrency and the repository guard. What only the real services can show is in the live check (tasks 6.x), each scenario named there.

**Regions.** Cloud Run in `us-east1`, near Render's Virginia region, and Neon in `aws-us-east-1`.

## Risks / Trade-offs

- [Vendor limits differ from the documentation] → task 1.1 checks pricing, the free allowances, Neon's branch, compute-hour and storage limits, and that `pg_restore --clean` into a branch with children works, before building.
- [A crawler keeps a preview busy] → `--max-instances 1` caps one preview at a single instance, the noindex header keeps well-behaved crawlers away, and the address is on the issue only. A budget alert emails Nate; it doesn't stop anything.
- [Cold starts] → the first request after an idle spell waits a few seconds for Cloud Run and Neon to wake.
- [A preview runs in a container, production on Render's Python runtime] → same requirements, Python version and commands, but a platform difference can still hide in either direction.
- [Pages with players show none] → without the player settings, event pages and the discovery deck show no players, and re-rendering saved event pages (`resave_all_events`) would strip their buttons, so previews never run it. A change to the listing row itself shows only for events saved after the change (open question 5).
- [A preview restarts from the base when its migrations fail] → what reviewers saved on it is lost. The workflow's log says so.
- [An idle preview's link goes dead] → after 7 days the bridge still shows the issue in `preview-ready`, with its deployment inactive. Rebuilding by hand restores it (open question 4).
- [The read-only role can read people's data] → `pg_dump` needs `SELECT` on every table it dumps the structure of. The credential stays in the `main`-only environment.

## Migration Plan

1. Task 1.1's checks, with Nate, on the new accounts.
2. Nate makes the read-only role and the secrets (tasks 1.3–1.5).
3. Merge. Run the nightly copy once by hand to make the first `base`.
4. The next code pull request gets a preview.
5. Rollback: disable the two workflows and run the sweep by hand with "remove all". Drop the read-only role if previews are given up.
