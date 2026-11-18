## Context

The live site runs on Render:
- a web service built by `bin/build.sh`, which installs, compiles the CSS, collects static files and migrates;
- a Postgres 17 database of about 20 MB;
- three cron jobs.

Static files are served by WhiteNoise. GitHub Actions (`django.yml`) runs the tests on every pull request.

Mail goes out through `core/digest_mail.py`. That module refuses to send (`MailNotReady`) unless `DEFAULT_FROM_EMAIL` is a real sender and `SITE_URL` is https. The views log a refusal without the address.

People's data is in:
- `Subscriber`, `SignInCode`, `DigestChoice`, `MailRequest`, `EmailSubscriber` and Django's sessions, which hold only people's data;
- Django's users (the admins);
- `Event.user_submission_email`.

The fork's `Dockerfile` is upstream's:
- Python 3.12.1, where production uses 3.11.14;
- `compilescss` and `collectstatic` read a `.env` build secret;
- the image starts `bin/serve.sh` on port 8000.

Cloud Run's figures:
- it serves a container at `https://<service>-<project number>.<region>.run.app`;
- it scales to zero;
- its monthly free allowance (180,000 vCPU-seconds, 360,000 GiB-seconds, 2 million requests) applies only in some regions, `us-east1` among them.

Neon's figures:
- a branch is a copy-on-write copy of its parent;
- a compute suspends after 5 idle minutes;
- the free plan allows 10 branches in a project.

## Goals / Non-Goals

**Goals:**
- personal data is removed once, in the nightly copy, so no preview branch ever holds it;
- one path from the live database: a read-only copy, once a night, from GitHub Actions;
- a preview's cost is near zero while nobody looks at it;
- everything is made and removed by workflows in the repository, with no hand steps per pull request.

**Non-Goals:**
- the issue side (intentable's follow-up);
- refreshing a preview's data while it lives. A preview keeps the copy it branched from until its pull request closes or it expires.

## Decisions

**The cleaning happens on the base, not on each preview.** `preview-base.yml` runs nightly. It:
1. runs `pg_dump --format=custom --no-owner --no-privileges` from `PREVIEW_SOURCE_DATABASE_URL` (the read-only role), with `--exclude-table-data` for the people-only tables and `django_session`;
2. restores the dump into a fresh Neon branch, `base-next`;
3. runs `scrub_preview_data` against `base-next`;
4. swaps `base-next` in as the new `base`, through Neon's API, and deletes the old base.

Previews branch only from `base`, which is always scrubbed, so a branch never holds personal data even for a moment. A failure before the swap leaves the old `base` in place.

The alternative was scrubbing each preview's branch after creating it. That repeats the work per preview, and a failed scrub would leave personal data in a branch that is served.

**GitHub Actions runs it all; Cloud Run only serves.** `preview.yml` runs on `pull_request` (`opened`, `synchronize`, `reopened`, `closed`) for pull requests whose head is in this repository. It also has a `paths-ignore` on `openspec/**` and `docs/**`.

On open or push, it:
1. builds the image and pushes it to Artifact Registry, tagged with the commit;
2. creates the Neon branch `pr-<n>` from `base` if it doesn't exist;
3. runs `migrate` and `scrub_preview_data --admin-only` (which sets `preview-admin`) from the image, against the branch;
4. deploys `preview-pr-<n>` to Cloud Run with `--min-instances 0 --max-instances 1 --allow-unauthenticated`;
5. records a GitHub deployment of `preview-pr-<n>` with the service's address.

On close, it deletes the service and the branch, and sets the deployment to `inactive`.

Running migrations from the runner, not at container start, keeps a failed migration from leaving a half-started service. The step fails the workflow, and the pull request shows it.

A Cloud Run revision tag per pull request on one shared service was considered. One service per pull request keeps each preview's settings and deletion separate, at no extra cost.

**Keyless sign-in.** GitHub Actions signs in to Google Cloud through Workload Identity Federation. It uses a service account limited to Cloud Run and Artifact Registry in the previews project, trusted only for this repository's workflows on `pull_request` and `schedule`. No Google key is stored. The secrets are `PREVIEW_SOURCE_DATABASE_URL`, `NEON_API_KEY` and `PREVIEW_ADMIN_PASSWORD`. GitHub doesn't give them to pull requests from forks or to Dependabot, and the workflow also skips those pull requests explicitly.

**Preview settings.** `nycnoise/settings/preview.py` extends `prod`:
- `ALLOWED_HOSTS` takes the service's `run.app` host;
- `SITE_URL` and the CSRF origin come from it;
- `DEFAULT_FROM_EMAIL` is empty, so `MailNotReady` refuses every email;
- every API, analytics and sheet-sync setting is empty;
- a small middleware adds `X-Robots-Tag: noindex, nofollow`.

The deploy passes only `DATABASE_URL`, `DJANGO_SECRET_KEY` (made per preview) and `DJANGO_SETTINGS_MODULE=nycnoise.settings.preview`. Cloud Run has no cron, so no job exists for a preview.

**The image matches Render.** The `Dockerfile`:
- becomes `python:3.11.14-slim`;
- installs `requirements.txt`;
- runs `compilescss` and `collectstatic` with placeholder settings, not a secret;
- starts gunicorn as `render.yaml`'s `startCommand` does, on `$PORT`.

`bin/serve.sh` stays for local use. CI gains a job that builds the image, so drift shows on the pull request that causes it.

**Sweep.** The nightly `preview-base.yml` also lists Cloud Run services and Neon branches named `pr-*`, and deletes each whose pull request is closed or has had no push for 7 days. That catches a missed `closed` event and keeps within Neon's 10 free branches.

**Regions.** Cloud Run in `us-east1` (in the free allowance, near Render's Virginia region) and Neon in `aws-us-east-1`.

## Risks / Trade-offs

- [Cold starts] → the first request after an idle spell waits for Cloud Run and Neon's compute to wake, a few seconds. Fine for review.
- [A preview runs in a container, production on Render's Python runtime] → the image is built from the same requirements, Python version and commands, and CI builds it, but a platform difference can still hide in either direction.
- [Neon's free plan: 10 branches] → the base plus 9 open previews. A tenth gets a failed workflow saying so (or Neon's paid plan, at $1.50 a branch-month).
- [Anyone with the address can open a preview] → it holds no personal data and asks not to be indexed. A password gate can be added if needed.
- [Cost surprise] → `--max-instances 1` caps each preview, and a budget alert on the project emails Nate at a few dollars.
- [A new people-only table is added later] → the exclusion list lives beside `scrub_preview_data`, whose test fails when a model with an `EmailField` is neither excluded nor scrubbed.
- [The live database refuses outside connections later] → the nightly copy moves to a Render cron job (open question 5).

## Migration Plan

1. Nate makes the Google Cloud project with billing and a budget alert, and the Neon project. With him, set up Workload Identity Federation, the read-only role and the GitHub secrets (tasks 1.x).
2. Merge. The nightly copy can be run by hand once, to make the first `base`.
3. The next code pull request gets a preview.
4. Rollback: disable the two workflows. The sweep, or a manual run of it, deletes what's left. Drop the read-only role if previews are given up.
