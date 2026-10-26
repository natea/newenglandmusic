## 1. Model

- [x] 1.1 Add `VenueFetchStatus` (venue one-to-one, fetched_at, source, found, upcoming, problems, nullable `job_run` with `SET_NULL`) and `JobRun.problems`, in one migration. Verify: `makemigrations --check` is clean and `migrate` applies locally.

## 2. Collecting problems

- [x] 2.1 Add `is_problem(note)` for the three failure prefixes, and have `RecordedCommand` store `self.job_problems` on the run. Verify: a test for the "Failed page and informational note" scenario, and a `RecordedCommand` test that problems are saved.
- [x] 2.2 In `fetch_events`, build `self.job_problems` from each venue's problem notes. Unless it's a dry run, save each fetched venue's `VenueFetchStatus` (source, found, upcoming, problems, job run) in one transaction. Verify: tests for the "Fetched venue" and "Dry run" scenarios, plus a check that a venue not selected keeps its status. All existing `fetch_events` tests still pass.

## 3. Admin

- [x] 3.1 Add the problems section and problems-count column to `JobRunAdmin`. Verify: tests for the "Run with problems" and "Run without problems" scenarios.
- [x] 3.2 Add the last-fetch column, the four-state filter and the "Event fetching" section to `VenueAdmin`, with `select_related("fetch_status")`. Verify: tests for the "Filter to problem venues", "Venue page" and "Never fetched" scenarios.

## 4. Check

- [x] 4.1 Run the full suite with outbound network blocked. Then run a real `fetch_events --sheet-ids` for a few venues that failed in the last full run (including V0594 Montage Music Hall), and check the job run's problem list and those venues' statuses in the admin. Verify: every test passes, and the failing venues show in red in both places.

## Workflow follow-up

- Archive with `/opsx:archive show-venue-fetch-problems` once every task is checked.
