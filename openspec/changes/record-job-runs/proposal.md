## Why

The pipeline's commands report what they did by printing it. Locally that output goes to `logs/`, but on Render each cron run starts on an empty disk, so those files vanish when the run ends. Render's Logs tab keeps the output only briefly, and it's a stream of text rather than a list of runs. Once the jobs are scheduled, nobody will be able to answer "did last night's fetch work, and what did it find?" without digging. A record of each run in the database, shown in the admin, answers that and survives restarts and database copies.

## What Changes

- **A record of each run:** every run of the five pipeline commands is saved as a job run:
  - the command and its arguments
  - when it started and finished
  - its outcome: running, succeeded or failed
  - whether it was a dry run
  - a short summary of counts
  - the report it printed
  - the error, if it failed
- **Commands:**
  - `sync_venues_from_gsheets`
  - `lookup_venue_places`
  - `check_event_sources`
  - `match_ticketmaster_venues`
  - `fetch_events`

  Each gives its own summary, for example "events created 12, updated 340, venues failed 3" for a fetch.
- **Runs that never finish:** a run that is killed, for example by running out of memory or a host timeout, can't record its own end. A run still marked running after a set time is shown as "didn't finish".
- **An admin page:** it lists runs newest first, with failed and unfinished runs easy to spot, and can be filtered by command and outcome. Each run shows its full report. Runs can't be added or edited by hand.
- **Old runs are pruned:** runs older than 90 days are deleted automatically, so the table stays small.
- **Output still prints as before,** so local logs and Render's Logs tab are unchanged.

## Capabilities

### New Capabilities

- `job-run-history`: recording each pipeline command run, with its outcome, summary and report, and reviewing the runs in the admin.

### Modified Capabilities

None. The commands' own behavior and printed output don't change.

## Impact

- **Models:** a new `JobRun` model, in one migration.
- **Code:**
  - a small `RecordedCommand` mixin, used by the five commands
  - one line or so per command to set its summary
- **Admin:** a read-only `JobRunAdmin`.
- **Docs:** `PRODUCTION.md`'s scheduled-jobs section says where to review runs. `AGENTS.md` mentions it under "The pipeline".
- **No external services:** recording adds no network calls.
