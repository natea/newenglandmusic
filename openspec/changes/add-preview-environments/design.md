## Context

`render.yaml` is the site's blueprint:
- the web service `newenglandmusic`;
- its Postgres 17 database;
- three cron jobs: `newenglandmusic-daily`, `newenglandmusic-weekly` and `newenglandmusic-digest`.

`bin/build.sh` installs, compiles the CSS, collects static files and runs `migrate`. The web service deploys only after GitHub Actions passes (`autoDeployTrigger: checksPass`).

Secrets are `sync: false` placeholders set in the dashboard, and the jobs copy them from the web service with `fromService`. The live database is about 20 MB.

Mail goes out through `core/digest_mail.py`. That module refuses to send (`MailNotReady`) unless `DEFAULT_FROM_EMAIL` is a real sender and `SITE_URL` is an https address. The views that send log a refusal without the address.

Personal data lives in a few places:
- `Subscriber`, `SignInCode`, `DigestChoice`, `MailRequest`, `EmailSubscriber` and Django's sessions, which hold only people's data;
- Django's users (the admins);
- `Event.user_submission_email`.

Render's preview environments copy the blueprint's services, databases and environment groups for each pull request:
- the copied databases start empty;
- `sync: false` variables aren't copied;
- `previewValue` overrides a variable in previews;
- `initialDeployHook` runs once after a preview's first successful deploy;
- `previews.expireAfterDays` deletes an idle preview;
- `previews.plan` and `previewPlan` set preview instance sizes.

## Goals / Non-Goals

**Goals:**
- a preview whose data is the live site's, minus people's data, in its own database;
- no path from a preview to the live database except one read-only copy at seed time;
- no email, outside API call, analytics or scheduled job from a preview.

**Non-Goals:**
- the loop's use of the preview (`preview-ready` and the "looks right?" question), which is intentable's follow-up;
- refreshing a preview's data after it is seeded. A new copy means a new preview: close and reopen the pull request, or wait for it to expire.

## Decisions

**Preview environments, not pull request previews.** A pull request preview shares the live `DATABASE_URL`, and `bin/build.sh` migrates. Making `build.sh` skip migrations when `IS_PULL_REQUEST` is true would still leave the preview reading and writing live data. Preview environments give each pull request its own database with no change to `build.sh`, because `fromDatabase` in a preview points at the preview's copy.

**The seed copies live data at seed time, through a read-only role.** `bin/preview-seed.sh` runs as the web service's `initialDeployHook`. It:
1. runs `pg_dump --format=custom --no-owner --no-privileges` from `PREVIEW_SOURCE_DATABASE_URL`, with `--exclude-table-data` for the people-only tables and `django_session`;
2. runs `pg_restore --clean --if-exists` into the preview's `DATABASE_URL`;
3. runs `migrate`, since the copy carries `main`'s schema and the pull request may add migrations that the first build's `migrate` applied to the empty database before the restore replaced it;
4. runs `scrub_preview_data`.

The role is a Postgres role on the live database with `SELECT` on the public schema and nothing else, made once by hand and recorded in `PRODUCTION.md`.

Alternatives considered:
- **A nightly cleaned dump in a private bucket.** That needs a job, a bucket and keys, and keeps a copy of live data at rest. It stays the fallback for open question 4.
- **The internal API that `populate_data_from_prod` uses.** It copies only events, venues and static pages, not acts and their links.

**The scrub runs before the preview is anyone's.** `initialDeployHook` runs after the first deploy, so for the minute the seed takes, the preview answers at an address nobody has yet. The bridge's follow-up posts the address only once the seed's deploy is reported. `scrub_preview_data`:
- sets each user's email to `user<id>@preview.invalid` and gives them an unusable password;
- empties `Event.user_submission_email`;
- deletes any row left in the people-only tables;
- creates or updates `preview-admin` as a superuser with `PREVIEW_ADMIN_PASSWORD`.

It refuses to run unless `IS_PULL_REQUEST` is `true`, so it can never touch the live database.

**Getting secrets into previews.** `PREVIEW_SOURCE_DATABASE_URL` and `PREVIEW_ADMIN_PASSWORD` go in an environment group, `preview-seed`, defined in `render.yaml` with `sync: false` values set in the dashboard. Only the web service links it. In production it does nothing, because only the seed reads it, and the seed refuses there. This rests on Render copying a group's dashboard values into previews, which task 1.1 checks before anything else is built.

**Cut off from the outside by preview values.** On the web service:
- `previewValue: ""` for `DEFAULT_FROM_EMAIL`, so `MailNotReady` refuses every email;
- `previewValue: ""` for the AWS keys, the API keys, `GOOGLE_SERVICE_ACCOUNT_JSON`, `POSTHOG_PROJECT_TOKEN` and `GOATCOUNTER_CODE`;
- `SITE_URL` left to fall back to `RENDER_EXTERNAL_URL`.

Most of these are `sync: false` and aren't copied anyway; the preview values make the intent explicit and survive a later change of how a variable is set. The cron jobs get `previews: generation: off`, so no job exists in a preview.

**Automatic, filtered, small and short-lived.** The blueprint's `previews.generation` is `automatic`, so the loop's pull requests get previews without changing their titles. The web service's `buildFilter.ignoredPaths` holds `openspec/**` and `docs/**`, so spec- and docs-only pull requests make none. `previews.expireAfterDays` is 7. The preview web service and database use the smallest paid plans; a free Postgres can't be used, because a workspace may have only one.

## Risks / Trade-offs

- [Render doesn't copy dashboard values of an environment group into previews] → task 1.1 checks it first. If not, switch to the bucket fallback before building the rest.
- [A new people-only table is added later and copied] → the seed's exclusion list lives next to `scrub_preview_data`, whose test fails when a model with an `EmailField` isn't excluded or scrubbed.
- [The seed's copy reads the live database during the day] → about 20 MB and a few seconds; read-only.
- [Preview cost] → each open pull request with code runs a web service and a database, billed by the second, on top of the Pro plan. Idle previews die after 7 days.
- [Stored event pages hold play buttons rendered with live keys] → they play without keys. Re-rendering pages in a preview (`resave_all_events`) would drop buttons, since the preview has no keys, so the seed doesn't re-render.
- [The first build migrates an empty database, then the restore replaces it] → harmless, and the seed migrates again after the restore.

## Migration Plan

1. Check that a group's dashboard value reaches a preview (task 1.1), on a throwaway pull request.
2. Make the read-only role on the live database and fill the `preview-seed` group in the dashboard.
3. Merge. Render's next blueprint sync turns previews on. Production's services are unchanged, except that the web service links the group.
4. Rollback: set `previews.generation` to `off` and sync. Open previews are deleted. Drop the read-only role if previews are given up.
