## MODIFIED Requirements

### Requirement: The daily job runs the daily pipeline in order
The daily job SHALL run, in this order: `sync_venues_from_gsheets`, `lookup_venue_places`, `lookup_venue_places --refresh-stale`, `fetch_events --all`, `match_spotify_artists --limit 500`, `match_apple_music_artists --limit 1000`, `resolve_artists_with_lastfm --limit 300`, `match_youtube_artists --limit 90` and `enrich_artists_from_musicbrainz --limit 100`. The artist matching runs daily, after the fetch, so new events' artists are matched the next morning, and a matching run cut short by a rate limit or quota carries on the next day. The Last.fm resolving runs after the Spotify and Apple Music matching, because it settles the names they found ambiguous. The YouTube matching runs before the MusicBrainz enrichment, so a slow or stopped enrichment never delays the listing's play buttons. The MusicBrainz enrichment runs last, and never with `--refresh`, so each morning looks up only records not looked up before.

#### Scenario: Daily run
- **WHEN** the daily job runs and every step succeeds
- **THEN** the nine commands run in that order, and the job succeeds

#### Scenario: Enrichment fails
- **WHEN** `enrich_artists_from_musicbrainz` fails during the daily job
- **THEN** the job exits with an error naming the enrichment, and the steps before it have already run
