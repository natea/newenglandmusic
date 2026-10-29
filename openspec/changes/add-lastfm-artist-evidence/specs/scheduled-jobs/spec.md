## MODIFIED Requirements

### Requirement: The daily job runs the daily pipeline in order
The daily job SHALL run, in this order: `sync_venues_from_gsheets`, `lookup_venue_places`, `lookup_venue_places --refresh-stale`, `fetch_events --all`, `match_spotify_artists --limit 500`, `match_apple_music_artists --limit 1000`, `resolve_artists_with_lastfm --limit 300` and `match_youtube_artists --limit 90`. The artist matching runs daily, after the fetch, so new events' artists are matched the next morning, and a matching run cut short by a rate limit or quota carries on the next day. The Last.fm resolving runs after the Spotify and Apple Music matching, because it settles the names they found ambiguous. The YouTube matching runs last, because it confirms artists that the steps before it found.

#### Scenario: Daily run
- **WHEN** the daily job runs and every step succeeds
- **THEN** the eight commands run in that order, and the job succeeds
