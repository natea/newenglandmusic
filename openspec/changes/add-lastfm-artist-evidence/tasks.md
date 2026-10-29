## 1. Clients and rules

- [x] 1.1 Add `core/lastfm.py`:
  - a `LastFm` client with an injectable session and sleep, at most two requests a second, sending the site's user agent;
  - `artist_info(name)` returning the MBID, listeners and bio summary, or None on error 6;
  - `top_track(name)` returning the first top track and its album, from `artist.getTopTracks` and `track.getInfo`;
  - `LastFmStopped` for errors 26 and 29;
  - error messages built from Last.fm's code and message only.
  
  Add fixtures in `core/tests/fixtures/lastfm/`. Verify with tests for pacing, the user agent, errors 6, 26 and 29, and the key's absence from errors.
- [x] 1.2 Add `artist(mbid)` to `core/music_ids.py`, returning the name, area, begin area, and the Spotify and Apple Music artist IDs from the URL relations, reusing the pacing and 503 retries. Extend `FakeWeb` with MBID lookups. Verify with tests for an artist with links, one without, and a 503 outage.
- [x] 1.3 Add `core/artist_evidence.py` with `covered_places()`, `names_covered_place()`, `shares_name()` and `is_dominant()`. Verify with unit tests for:
  - "Massachusetts", "Somerville, MA" and a venue town matching;
  - "Brighton" and "Germany" not matching;
  - the shared-name notes ("There are at least two…", "There are several…", "There are 2…", numbered acts);
  - the 100,000-listener threshold.

## 2. Models

- [x] 2.1 Add `Source.EVIDENCE` and a nullable `evidence_checked_at` to `SpotifyArtistLink` and `AppleMusicArtistLink`, with a migration. Make both matching commands' `is_due` treat evidence links as they treat an editor's. Verify with tests that `match_spotify_artists` makes no search for an evidence link, and that `match_apple_music_artists` refreshes its top song but keeps its artist. Also verify that `makemigrations --check` is clean.

## 3. Resolving

- [x] 3.1 Add `resolve_artists_with_lastfm` (a `RecordedCommand`) with `--names`, `--limit` (default 300), `--dry-run` and `--revert`. It:
  - considers due ambiguous links, and re-checks evidence links matched more than 30 days ago;
  - applies the ID chain and the place or dominance rule;
  - looks up Apple top songs;
  - re-renders the affected events;
  - stops cleanly on `LastFmStopped` and `MusicBrainzBusy`;
  - records the job summary counts.
  
  Verify with tests for every scenario in `specs/lastfm-artist-evidence/spec.md`: local act, dominant touring act, shared name flagged, small act from elsewhere, no MBID or link, different name on MusicBrainz, Apple Music link resolved, recently considered, Spotify matching leaves it alone, revert, evidence gone, nothing kept, rate limited, key out of errors, and not configured.

## 4. YouTube

- [x] 4.1 In `match_youtube_artists`, when a name has no Apple top song and its own Spotify link is matched, take the song and album from `LastFm.top_track()`, unless `shares_name()` flags its bio, and run the same `confirming_video` check. `LastFmStopped` ends the Last.fm route for the run, but not the run. Verify with tests for:
  - a Spotify-only artist confirmed by its Last.fm top track;
  - a shared Last.fm page;
  - a Spotify-only artist with no ID link and no Last.fm page or top tracks.
  
  Also verify that the existing YouTube tests still pass.

## 4b. YouTube songs from Last.fm only

- [x] 4b.1 In `match_youtube_artists`, take the song and album only from `LastFm.top_track()`, for names matched on Spotify or Apple Music on their own link, unless `shares_name()` flags the bio. Remove the Apple Music client. Only let a Topic video confirm when Last.fm gives an album. Rework the existing song tests to use Last.fm fixtures. Verify with tests for:
  - Topic channel recording;
  - same name, different band;
  - cover or fan upload;
  - not embeddable;
  - a Spotify-only artist confirmed;
  - Apple Music data isn't used (no Apple client made);
  - a Topic video with no album from Last.fm;
  - a shared Last.fm page;
  - a Spotify-only artist with no ID link.
- [x] 4b.2 Add `song_source` (blank, "apple" or "lastfm") to `YouTubeArtistLink`, with a migration that sets "apple" on automatic links with evidence "topic-song" or "channel-song". In the command, treat those links as due for a full re-match, and record new song matches with "lastfm". Verify with tests for:
  - an old match confirmed again;
  - an old match not confirmed, which loses its button;
  - editor and ID-linked links unaffected.
  
  Also verify the migration on a test database.

## 5. Configuration and docs

- [x] 5.1 Add `LASTFM_API_KEY` to `.env.example`, `render.yaml` (the web service, and the daily cron from it), AGENTS.md and PRODUCTION.md, including what Last.fm's terms ask and the launch-checklist item to ask partners@last.fm. Add `resolve_artists_with_lastfm --limit 300` to `bin/daily.sh` before the YouTube step, and update `DAILY` and the cron's expected keys in `core/tests/test_scheduled_jobs.py`. Verify that the scheduled-jobs tests pass with eight daily steps.

## 6. Check

- [x] 6.1 Run the whole suite with outbound network blocked. Then run `resolve_artists_with_lastfm --dry-run --limit 30` locally, and check each proposed resolution by hand against Spotify and MusicBrainz. Also run `match_youtube_artists --dry-run --limit 10`, and check its Last.fm-based matches on YouTube. Verify that the tests pass, and that every proposed resolution and match is the right act.
