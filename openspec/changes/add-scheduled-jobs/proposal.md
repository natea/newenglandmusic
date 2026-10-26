## Why

The site is deployed on Render, but nothing runs the pipeline there: the sheet sync, the Places lookups and event fetching only happen when someone runs them by hand. Events go stale. And Google's terms make one job urgent: the coordinates stored on Render were last fetched on 2026-10-25, and from 2026-11-24 they're older than the 30 days the terms allow, unless the daily `lookup_venue_places --refresh-stale` is running. Render holds all the API keys the jobs need, except `GOOGLE_PLACES_API_KEY`.

## What Changes

- **Two Render cron jobs**, defined in `render.yaml` next to the web service:
  - **Daily** (10:00 UTC, about 5 or 6 am in New England): sync the venue sheet, look up new venues on Google Places, refresh stale coordinates, and fetch every venue's events.
  - **Weekly** (Sundays at 07:00 UTC, before that day's daily run): check every venue's event sources, then match venues to Ticketmaster and to Eventbrite organizers.
- **Two scripts**, `bin/daily.sh` and `bin/weekly.sh`, run each job's commands in order. A failed command doesn't stop the later ones, which don't depend on it succeeding. The script then exits with an error, so Render marks the run failed. Each command's own run is still recorded at `/admin/core/jobrun/`.
- **Keys:** the cron jobs read the web service's secrets through `fromService` references in the blueprint, so each key is set once. `GOOGLE_PLACES_API_KEY` is added to the web service.
- **A lighter build** for the cron jobs, `bin/build-job.sh`, which only installs the requirements. Migrations stay in the web service's build, so they never run twice at once.
- **Docs:** `PRODUCTION.md`'s schedule section describes the jobs as set up, and drops the launch checklist's "scheduled jobs added" item once they run.

## Capabilities

### New Capabilities

- `scheduled-jobs`: running the pipeline commands on a schedule on the host, and how a failed step is handled and reported.

### Modified Capabilities

None. The commands themselves don't change.

## Impact

- **Files:** `render.yaml`, new `bin/daily.sh`, `bin/weekly.sh` and `bin/build-job.sh`, `PRODUCTION.md`, `AGENTS.md`.
- **Tests:** the scripts are run against a stub `python` that records each call and can fail one, and `render.yaml` is checked for the jobs, their commands and keys. No network.
- **Cost:**
  - **Render:** about $2 a month. Each cron job is billed by the second of running time, with a $1 minimum a month, on the `0.5c-512mb` plan.
  - **Anthropic:** about $9 a month for the daily full fetch, as `PRODUCTION.md` already estimates.
  - **Google Places:** inside the 5,000 free calls a month.
- **Setup by the user:** creating the two cron services means a blueprint sync in the Render dashboard, which shows the new services and their cost for approval. Copying `GOOGLE_PLACES_API_KEY` to Render needs the user's go-ahead.
- **Not covered:** the free Render database expires on 2026-11-24 and is deleted 14 days later. These jobs don't change that, and it needs its own decision before then.
