## 1. Model and recording

- [x] 1.1 Add `JobRun` (command, arguments, started_at, finished_at, status, dry_run, summary, output, error, with indexes on started_at and command) and its migration. Verify: `makemigrations --check` is clean and `migrate` applies locally.
- [x] 1.2 Add the `RecordedCommand` mixin in `core/job_runs.py`. It overrides `execute()`, creates the row and prunes runs over 90 days old, tees stdout, saves the outcome, summary, output (with the 200,000-character limit) and error, re-raises failures, and never lets a recording error break the command. Verify: tests with a test-only command for the "Very long report" and "Pruning" scenarios, and for a recording error leaving the command's result unchanged.

## 2. The five commands

- [x] 2.1 Use `RecordedCommand` in `sync_venues_from_gsheets`, `lookup_venue_places`, `check_event_sources`, `match_ticketmaster_venues` and `fetch_events`, and set `self.job_summary` in each from the counts it already prints. Verify: tests for the "Successful run", "Dry run", "Output unchanged", "Fetch summary" and "Missing API key" scenarios, using the commands' existing mocks. All existing command tests still pass.

## 3. Admin

- [x] 3.1 Add a read-only `JobRunAdmin`: newest first; command, started, duration, outcome and summary columns; command and outcome filters, including "didn't finish"; red labels for failed and unfinished runs; output and error shown in full on each run's page. Verify: tests for the "Killed run", "Run in progress", "Failed run stands out" and "Read-only" scenarios.

## 4. Docs and check

- [x] 4.1 Say in `PRODUCTION.md`'s scheduled-jobs section, and in `AGENTS.md`'s pipeline section, that each run is recorded and reviewed at `/admin/core/jobrun/`. Verify by reading both.
- [x] 4.2 Run the full suite with outbound network blocked. Then run `fetch_events --dry-run --per-source 1 --skip-ai` and a `match_ticketmaster_venues` without the key locally, and check both runs in the admin. Verify: every test passes, and the admin shows one succeeded dry run and one failed run with its error.

## Workflow follow-up

- Archive with `/opsx:archive record-job-runs` once every task is checked.
- Possible follow-up: email an admin when a scheduled run fails or doesn't finish.
