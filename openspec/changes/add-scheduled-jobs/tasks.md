## 1. Scripts and configuration

- [x] 1.1 Add `bin/daily.sh` and `bin/weekly.sh`, which run their steps in order, keep going after a failure, print each step and a summary, and exit 1 if any failed; and `bin/build-job.sh`, which only installs the requirements. Verify: tests running the scripts against a stub `python` for "Daily run", "Weekly run" and "Sheet sync fails", and a check that every command the scripts name is a management command.
- [x] 1.2 Add the two cron services to `render.yaml`: schedules `0 10 * * *` and `0 7 * * 0`, `bin/build-job.sh`, `autoDeployTrigger: checksPass`, plan `0.5c-512mb`, `DATABASE_URL` from the database, and the keys each needs from the web service. Confirm the `fromService` / `envVarKey` syntax against Render's blueprint schema first. Verify: a test for "Configuration" that parses `render.yaml`.

## 2. Docs

- [x] 2.1 Update `PRODUCTION.md` (the schedule as set up, the blueprint sync step, the Places key, cost) and `AGENTS.md` (the scripts). Verify by reading both.

## 3. Rollout

- [x] 3.1 With the user's go-ahead, add `GOOGLE_PLACES_API_KEY` to the web service. Verify: it's listed on the service (checked without printing it).
- [x] 3.2 Run the full suite with outbound network blocked, then release. The user runs the blueprint sync that creates the cron services. Verify: both services exist with their schedules.
- [x] 3.3 Trigger each job once by hand. Verify: each succeeds, its job runs appear in the admin, the refresh leaves no coordinates older than 30 days, and the measured durations and memory are recorded in design.md. (2026-10-26: weekly succeeded in 4.5 min after the memory fix, daily in 13 min; no coordinates are older than 30 days on Render.)
