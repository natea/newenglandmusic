# scheduled-jobs Specification

## Purpose

Run the venue and event pipeline on a schedule on the host, in dependency order, so the site's venues, coordinates and events stay current without anyone running commands by hand.

## Requirements

### Requirement: The daily job runs the daily pipeline in order
The daily job SHALL run, in this order: `sync_venues_from_gsheets`, `lookup_venue_places`, `lookup_venue_places --refresh-stale`, `fetch_events --all`, `match_spotify_artists --limit 500`, `match_apple_music_artists --limit 1000`, `resolve_artists_with_lastfm --limit 300`, `match_youtube_artists --limit 90` and `enrich_artists_from_musicbrainz --limit 100`. The artist matching runs daily, after the fetch, so new events' artists are matched the next morning, and a matching run cut short by a rate limit or quota carries on the next day. The Last.fm resolving runs after the Spotify and Apple Music matching, because it settles the names they found ambiguous. The YouTube matching runs before the MusicBrainz enrichment, so a slow or stopped enrichment never delays the listing's play buttons. The MusicBrainz enrichment runs last, and never with `--refresh`, so each morning looks up only records not looked up before.

#### Scenario: Daily run
- **WHEN** the daily job runs and every step succeeds
- **THEN** the nine commands run in that order, and the job succeeds

#### Scenario: Enrichment fails
- **WHEN** `enrich_artists_from_musicbrainz` fails during the daily job
- **THEN** the job exits with an error naming the enrichment, and the steps before it have already run

### Requirement: The weekly job runs the source check and matching in order
The weekly job SHALL run, in this order: `check_event_sources`, `match_ticketmaster_venues`, `match_eventbrite_organizers`, `match_seatgeek_venues`, `lookup_venue_neighborhoods` and `read_artist_link_hubs`. The link-hub reading runs last, after the venue steps. A failure in it SHALL fail the run without stopping the other steps, as the other steps do, and it SHALL be recorded as a `JobRun` with a summary of the records read, filled, flagged and failed.

#### Scenario: Weekly run
- **WHEN** the weekly job runs and every step succeeds
- **THEN** the six commands run in that order, the job succeeds, and the hub step's summary is listed at `/admin/core/jobrun/`

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
