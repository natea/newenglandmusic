## Purpose

Run the venue and event pipeline on a schedule on the host, in dependency order, so the site's venues, coordinates and events stay current without anyone running commands by hand.

## ADDED Requirements

### Requirement: The daily job runs the daily pipeline in order
The daily job SHALL run, in this order: `sync_venues_from_gsheets`, `lookup_venue_places`, `lookup_venue_places --refresh-stale`, `fetch_events --all`, `match_spotify_artists --limit 1000` and `match_apple_music_artists --limit 1000`. The artist matching runs daily, after the fetch, so new events' artists are matched the next morning, and a matching run cut short by a rate limit carries on the next day.

#### Scenario: Daily run
- **WHEN** the daily job runs and every step succeeds
- **THEN** the six commands run in that order, and the job succeeds

### Requirement: The weekly job runs the source check and matching in order
The weekly job SHALL run, in this order: `check_event_sources`, `match_ticketmaster_venues`, and `match_eventbrite_organizers`.

#### Scenario: Weekly run
- **WHEN** the weekly job runs and every step succeeds
- **THEN** the three commands run in that order, and the job succeeds

### Requirement: A failed step doesn't stop the job, but fails it
When a step fails, the job SHALL still run the steps after it, and SHALL end with a failing exit status, naming the steps that failed.

#### Scenario: Sheet sync fails
- **WHEN** `sync_venues_from_gsheets` fails during the daily job
- **THEN** the lookups and the fetch still run, and the job exits with an error naming the sync

### Requirement: The jobs are scheduled on the host with the site's keys
The host configuration SHALL define a daily job and a weekly job, the weekly one running before the daily run on the same day. Each SHALL get the database and the API keys its commands need from the web service and the database, so each key is set in one place. The jobs SHALL NOT run migrations.

#### Scenario: Configuration
- **WHEN** `render.yaml` is read
- **THEN** it defines both cron jobs with their schedules and scripts, each lists the keys its commands use from the web service, and neither job's build runs migrations
