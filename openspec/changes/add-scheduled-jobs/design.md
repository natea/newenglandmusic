## Context

- **The pipeline** (AGENTS.md): `sync_venues_from_gsheets` → `lookup_venue_places` (and `--refresh-stale`) → `check_event_sources` → `match_ticketmaster_venues` / `match_eventbrite_organizers` → `fetch_events`. Each run is recorded as a `JobRun`.
- **PRODUCTION.md's suggested schedule:** sync, lookups and fetching daily; the source check and matching weekly, because the check crawls every venue's site.
- **Render cron jobs** (render.com/docs/cronjobs):
  - billed by the second of running time, with a $1 minimum a month per job
  - schedules are cron expressions in UTC
  - at most one run of a job is active at a time; a scheduled run waits for an active one to finish
  - runs are stopped after 12 hours
- **The web service** builds with `bin/build.sh`, which installs requirements, compiles SCSS, collects static files and migrates. It deploys a commit only after CI passes (`autoDeployTrigger: checksPass`). Its secrets were set by hand or through Render's API, not in `render.yaml` (`sync: false`).
- **Run lengths:** no full run has been timed yet. One-off jobs on Render took about a minute for 37 venues; a full `fetch_events --all` covers about 600 and is estimated at 10 to 30 minutes.

## Goals / Non-Goals

**Goals:**
- The pipeline runs unattended on Render, in dependency order, on the suggested schedule.
- The daily coordinate refresh runs, so stored coordinates never pass Google's 30 days.
- A failure in one step is visible (a failed Render run, a failed `JobRun`) without blocking the steps that don't need it.
- Each secret is set in one place.

**Non-Goals:**
- An in-app scheduler or task queue. PRODUCTION.md's "Why not Celery?" still holds.
- Alerting beyond Render's own notifications for failed runs and the job-run admin.
- The database plan. Its expiry is a separate decision.

## Decisions

**Two jobs, each running a script.** One cron service per schedule keeps the cost at two $1 minimums, and keeps the order between commands inside a script, where it's explicit and testable. Running each command as its own cron service would cost more, and couldn't guarantee order.

**Steps run on after a failure; the run still fails.** The scripts don't use `set -e`. Each step runs, its exit status is remembered, and the script exits 1 at the end if any failed. The steps don't depend on one another succeeding:
- a sheet sync that fails leaves the venues as they were, and they can still be fetched;
- a failed Places lookup leaves the sheet coordinates in place;
- a failed match leaves existing links.

The script prints a line before each step and a summary at the end, which appear in the run's Render log.

**Order inside the daily job:** sync, lookup, refresh, fetch. The refresh runs after the lookup, as PRODUCTION.md says, and both before the fetch, so newly synced venues have coordinates when their events are saved.

**The weekly job runs before Sunday's daily one.** At 07:00 UTC, three hours before it. If it overruns, Render's no-overlap rule applies only within a job, so the two could overlap on Sundays; the commands don't conflict (the fetch reads saved sources, which the check replaces per venue in one transaction).

**Keys come from the web service.** Each cron job lists the keys it needs with `fromService` (`type: web`, `name: newenglandmusic`, `envVarKey: <key>`), and `DATABASE_URL` from the database, like the web service. The exact syntax is checked against Render's blueprint schema in task 1. If references to `sync: false` values don't work, the fallback is an environment group holding the keys, attached to all three services.

**A lighter build for the jobs.** `bin/build-job.sh` only runs `pip install -r requirements.txt`. The jobs don't serve pages, so they need no static files, and migrating from three services at once could race. A job built from a commit whose migrations haven't run yet would fail its run, so the jobs use `autoDeployTrigger: checksPass` like the web service.

**Plan:** `0.5c-512mb`, the cheapest. The fetch runs Scrapy and up to 8 AI extraction threads. If the first runs run out of memory, the daily job moves to `1c-2g`, and this design is updated with the measured peak.

## Risks / Trade-offs

- [Render's IP addresses get blocked by more venue sites than a home connection.] → The fallback to linked APIs covers linked venues. The weekly-only crawl limits how often we hit each site. Blocked venues show in the fetch-problems filter.
- [A run fails and nobody notices.] → Render emails the workspace about failed cron runs by default, and the job-run admin lists failures.
- [The daily fetch costs more than estimated.] → Its Anthropic usage is printed in each run, and `--skip-ai` can be added to the script.
- [The free database expires on 2026-11-24.] → Out of scope here; listed so it isn't forgotten.

## Migration Plan

1. Add `GOOGLE_PLACES_API_KEY` to the web service, with the user's go-ahead.
2. Merge to `main`. The user runs a blueprint sync in the Render dashboard, which creates the two cron services after showing their cost.
3. Trigger each job once by hand from the dashboard or CLI, and check its log and job runs.

**Rollback:** suspend or delete the cron services in the dashboard, and revert `render.yaml`.

## Open Questions

- **Durations and memory** of a full run on Render. Measured on the first manual runs, and recorded here.
