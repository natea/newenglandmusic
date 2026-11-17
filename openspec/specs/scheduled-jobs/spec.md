# scheduled-jobs Specification

## Purpose

Run the venue and event pipeline on a schedule on the host, in dependency order, so the site's venues, coordinates and events stay current without anyone running commands by hand.

## Requirements

### Requirement: The daily job runs the daily pipeline in order
The daily job SHALL run, in this order: `lookup_venue_places`, `lookup_venue_places --refresh-stale`, `fetch_events --all`, `match_spotify_artists --limit 500`, `match_apple_music_artists --limit 1000`, `resolve_artists_with_lastfm --limit 300`, `match_youtube_artists --limit 90` and `enrich_artists_from_musicbrainz --limit 100`. It SHALL NOT run `sync_venues_from_gsheets`: venues are kept in the admin. The artist matching runs daily, after the fetch, so new events' artists are matched the next morning, and a matching run cut short by a rate limit or quota carries on the next day. The Last.fm resolving runs after the Spotify and Apple Music matching, because it settles the names they found ambiguous. The YouTube matching runs before the MusicBrainz enrichment, so a slow or stopped enrichment never delays the listing's play buttons. The MusicBrainz enrichment runs last, and never with `--refresh`, so each morning looks up only records not looked up before.

#### Scenario: Daily run
- **WHEN** the daily job runs and every step succeeds
- **THEN** the eight commands run in that order, and the job succeeds

#### Scenario: Enrichment fails
- **WHEN** `enrich_artists_from_musicbrainz` fails during the daily job
- **THEN** the job exits with an error naming the enrichment, and the steps before it have already run

### Requirement: The weekly job runs the source check and matching in order
The weekly job SHALL run, in this order: `check_event_sources`, `match_ticketmaster_venues`, `match_eventbrite_organizers`, `match_seatgeek_venues` and `lookup_venue_neighborhoods`. It SHALL NOT run `read_artist_link_hubs` or `find_bandcamp_embeds`: the link hubs' robots.txt forbids reading them, and Bandcamp challenges requests from the host's servers, so both run by hand. A failure in a step SHALL fail the run without stopping the other steps.

#### Scenario: Weekly run
- **WHEN** the weekly job runs and every step succeeds
- **THEN** the five commands run in that order and the job succeeds

#### Scenario: Not scheduled
- **WHEN** the daily, weekly or weekly-email job runs
- **THEN** neither `read_artist_link_hubs` nor `find_bandcamp_embeds` runs

### Requirement: The jobs are scheduled on the host with the site's keys
The host configuration SHALL define a daily job and a weekly job, the weekly one running before the daily run on the same day. Each SHALL get the database and the API keys its commands need from the web service and the database, so each key is set in one place. The jobs SHALL NOT run migrations.

#### Scenario: Configuration
- **WHEN** `render.yaml` is read
- **THEN** it defines both cron jobs with their schedules and scripts, each lists the keys its commands use from the web service, and neither job's build runs migrations

### Requirement: A failed step fails the job without stopping it
When a step fails, the job SHALL still run the steps after it, and SHALL end with a failing exit status, naming the steps that failed.

#### Scenario: Places lookup fails
- **WHEN** `lookup_venue_places`, the daily job's first step, fails
- **THEN** the other lookups and the fetch still run, and the job exits with an error naming the lookup
