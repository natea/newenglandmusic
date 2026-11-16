## MODIFIED Requirements

### Requirement: The daily job runs the daily pipeline in order
The daily job SHALL run, in this order: `lookup_venue_places`, `lookup_venue_places --refresh-stale`, `fetch_events --all`, `match_spotify_artists --limit 500`, `match_apple_music_artists --limit 1000`, `resolve_artists_with_lastfm --limit 300`, `match_youtube_artists --limit 90` and `enrich_artists_from_musicbrainz --limit 100`. It SHALL NOT run `sync_venues_from_gsheets`: venues are kept in the admin. The artist matching runs daily, after the fetch, so new events' artists are matched the next morning, and a matching run cut short by a rate limit or quota carries on the next day. The Last.fm resolving runs after the Spotify and Apple Music matching, because it settles the names they found ambiguous. The YouTube matching runs before the MusicBrainz enrichment, so a slow or stopped enrichment never delays the listing's play buttons. The MusicBrainz enrichment runs last, and never with `--refresh`, so each morning looks up only records not looked up before.

#### Scenario: Daily run
- **WHEN** the daily job runs and every step succeeds
- **THEN** the eight commands run in that order, and the job succeeds

#### Scenario: Enrichment fails
- **WHEN** `enrich_artists_from_musicbrainz` fails during the daily job
- **THEN** the job exits with an error naming the enrichment, and the steps before it have already run

## REMOVED Requirements

### Requirement: A failed step doesn't stop the job, but fails it
**Reason**: Its scenario named the sheet sync, which leaves the daily job; replaced by "A failed step fails the job without stopping it", whose scenario names the new first step.
**Migration**: None; the behavior is unchanged.

## ADDED Requirements

### Requirement: A failed step fails the job without stopping it
When a step fails, the job SHALL still run the steps after it, and SHALL end with a failing exit status, naming the steps that failed.

#### Scenario: Places lookup fails
- **WHEN** `lookup_venue_places`, the daily job's first step, fails
- **THEN** the other lookups and the fetch still run, and the job exits with an error naming the lookup
