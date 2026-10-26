## Purpose

Keep a reviewable history of the pipeline's command runs in the database: what ran, when, whether it worked, what it found and what it printed. This lets scheduled jobs be checked from the admin after the host's own logs are gone.

## ADDED Requirements

### Requirement: Each pipeline command run is recorded

Each run of `sync_venues_from_gsheets`, `lookup_venue_places`, `check_event_sources`, `match_ticketmaster_venues` and `fetch_events` SHALL be saved as a job run. The record SHALL be created when the run starts, with status running, and SHALL hold the command's name, its arguments, the start time and whether it is a dry run. When the run ends, the record SHALL be updated with the end time and the status succeeded or failed. The command's printed output SHALL be unchanged.

#### Scenario: Successful run

- **WHEN** `fetch_events --all` runs and finishes normally
- **THEN** one job run is saved for `fetch_events`, with the arguments `--all`, a start and end time, and status succeeded

#### Scenario: Dry run

- **WHEN** `fetch_events --dry-run --per-source 1` runs
- **THEN** its job run is marked as a dry run

#### Scenario: Output unchanged

- **WHEN** a recorded command runs
- **THEN** it prints exactly what it printed before recording existed

### Requirement: A run's report and summary are kept

A job run SHALL keep the report the command printed to its standard output. Each command SHALL also record a short summary of counts, which the admin list shows.

#### Scenario: Fetch summary

- **WHEN** a fetch creates 12 events, updates 340 and fails for 3 venues
- **THEN** its job run's summary shows those three counts, and its report holds the printed per-venue report

#### Scenario: Very long report

- **WHEN** a command prints more than the report limit
- **THEN** the job run keeps the start and end of the report, and says how much was left out

### Requirement: Failures are recorded

When a command fails with an error, its job run SHALL be marked failed, with the error message and traceback and the report printed up to that point. The command SHALL still fail as it does today, with the same error and exit status.

#### Scenario: Missing API key

- **WHEN** `match_ticketmaster_venues` runs without `TICKETMASTER_API_KEY`
- **THEN** its job run is marked failed with the error "TICKETMASTER_API_KEY is not set", and the command still exits with that error

### Requirement: Runs that never finish are flagged

A job run still marked running more than 6 hours after it started SHALL be shown as "didn't finish" wherever runs are listed. Its stored status SHALL be left as it is.

#### Scenario: Killed run

- **WHEN** a fetch's job run started 7 hours ago and was never marked finished
- **THEN** the admin list shows it as didn't finish

#### Scenario: Run in progress

- **WHEN** a fetch's job run started 10 minutes ago and is still running
- **THEN** the admin list shows it as running

### Requirement: Admins can review runs

The admin SHALL list job runs newest first, showing each run's command, start time, duration, outcome and summary. Failed and unfinished runs SHALL stand out. The list SHALL be filterable by command and by outcome. Each run's page SHALL show its arguments, report and any error. Job runs SHALL NOT be added or edited in the admin.

#### Scenario: Failed run stands out

- **WHEN** an admin opens the job run list, and the latest fetch failed
- **THEN** that run is listed first, marked failed, and shows its error on its own page

#### Scenario: Read-only

- **WHEN** an admin opens a job run's page
- **THEN** there is no way to change its fields or to add a new job run

### Requirement: Old runs are pruned

Job runs that started more than 90 days ago SHALL be deleted when a new run is recorded.

#### Scenario: Pruning

- **WHEN** a command runs, and there are job runs from 100 days ago and from 10 days ago
- **THEN** the 100-day-old runs are deleted and the 10-day-old ones are kept
