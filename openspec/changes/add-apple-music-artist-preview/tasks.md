## 1. Client and model

- [x] 1.1 Add `PyJWT` and `cryptography` to `requirements.txt` with `uv pip install`, pinned, and add `APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_KEY_ID`, `APPLE_MUSIC_PRIVATE_KEY` and `APPLE_MUSIC_PREVIEWS` to `.env.example`, `render.yaml` (the web service with `sync: false`, and the daily job with `fromService`; the weekly job no longer runs artist matching) and `core/test_runner.py`'s stripped keys. Verify that `manage.py check` and the scheduled-jobs tests pass.
- [x] 1.2 Write `core/apple_music.py`. Verify it with 1.4. It has:
  - `credentials()`;
  - `developer_token()`, an ES256 JWT with `iss` and `kid`, a one-hour `exp`, cached, and `\n` in the key restored;
  - `AppleMusicClient(session, sleep, clock)`, which spaces requests 0.5 seconds apart, waits for `Retry-After` and backs off on 429 for at most three tries, and raises `AppleMusicAuthError` on 401;
  - `search_artists(name)` and `top_song(artist_id)`, which takes the album ID from the song's URL;
  - `parse_artist_id(url)`;
  - `previews_enabled()`.
- [x] 1.3 Add the `AppleMusicArtistLink` model, with `name_key` (unique), `status`, `apple_artist_id`, `top_song_id`, `top_album_id`, `source`, `checked_at` and `last_seen_at`, and its migration. Verify that `makemigrations --check` is clean.
- [x] 1.4 Add fixtures in `core/tests/fixtures/apple_music/` (a unique match, same-name artists, no exact match, top songs with and without results, a 429 and a 401), and `core/tests/test_apple_music_client.py`. Verify that it passes offline. It covers:
  - the token verifying with a generated test key's public half, with `iss`, `kid` and an `exp` no more than an hour after `iat`;
  - throttling, `Retry-After` then success, and three 429s raising;
  - a 401 raising `AppleMusicAuthError`;
  - the album ID parsed from the song URL;
  - artist URL parsing, valid and a Spotify URL rejected;
  - that no key or token appears in error messages.

## 2. Matching command

- [x] 2.1 Write the `match_apple_music_artists` `RecordedCommand`. Verify it with 2.2. It:
  - collects names with `event_artist_names`, and updates `last_seen_at`;
  - deletes links unseen for 30 days;
  - searches new and stale automatic names;
  - refreshes the top song of every matched link more than 30 days old, editors' included;
  - records matched (with the top song), ambiguous or not found;
  - counts failures and continues, but stops on `AppleMusicAuthError`;
  - re-renders events whose links changed;
  - supports `--names`, `--limit` and `--dry-run`;
  - exits 0 without doing anything when not configured;
  - sets `job_summary`.
- [x] 2.2 Add `core/tests/test_match_apple_music_artists.py`, covering every matching, top-song, refresh and expiry, and rate-limit scenario in the spec: a unique match, same-name artists, no exact match, not configured, a dry run, the top song recorded, no top songs, a refresh after 30 days, an editor's match getting a new top song, a link no longer needed, a changed song re-rendered, rate limited then succeeding, a persistent failure, and bad credentials stopping the run. Verify that it passes offline.

## 3. Admin

- [x] 3.1 Add an admin page for `AppleMusicArtistLink`. It has status and source filters, an Apple Music artist URL field (parsed, then its top song looked up through the client), and "no Apple Music artist" as a field and an action. Saving re-renders the events that name the link. Verify with 3.2.
- [x] 3.2 Add `core/tests/test_admin_apple_music_link.py`, covering an editor setting a match (with the top song looked up through the mocked client), an invalid link rejected, and an editor marking no artist. Verify that it passes.

## 4. Listing

- [x] 4.1 Change `bake_event_html` to pass `artist_previews`, a list of (name, Spotify ID or none, Apple artist, song and album IDs or none). Render both buttons in the row of `event.html`, renamed `artist-previews`, the Apple one only when configured and `APPLE_MUSIC_PREVIEWS` is on. Rename `spotify_preview.js` to `artist_preview.js`, and add the Apple branch: the song iframe with Apple's attributes, plus the "More by …" link, with one `.artist-player` across both services. Add an Apple mark style. Verify with 4.2 and 4.3.
- [x] 4.2 Add render tests, covering the Apple button beside the Spotify one, Apple only, no Apple iframe before a click, switched off, and no private key or token in the HTML, and update the Spotify render tests for the renamed row and context. Verify that they pass.
- [x] 4.3 Rename the browser test to `test_artist_preview_browser.py`, and add the Apple scenarios: a click opens the top song with the right `src` and the artist link, and one player across services. Verify that the whole browser test passes offline.

## 5. Docs and check

- [x] 5.1 Add `step python manage.py match_apple_music_artists` to `bin/daily.sh`, after `match_spotify_artists`, and update `core/tests/test_scheduled_jobs.py`. Add an "Apple Music play buttons" section to `PRODUCTION.md`, with the credential steps from `design.md`'s migration plan, and add the variables to `AGENTS.md`. Verify that `bash -n bin/daily.sh` and the scheduled-jobs tests pass.
- [x] 5.2 Run the whole suite with outbound network blocked. Then, with real credentials, run `match_apple_music_artists --dry-run --limit 30`, logged to `logs/match_apple_music_artists-YYYY-MM-DD.log`, and spot-check each matched artist and top song in a browser. Verify that the tests pass and that the spot-checked matches are right, or record the wrong ones as rule fixes.
  - 2026-10-27: 9 of 30 names matched. In Apple's player, 13 Scotland Rd, The 860 and A Foreigner's Journey To Boston were right; "404 Band" matched a different act of that name, a name collision for editors to fix in the admin (Spotify matched it the same way). The run also showed Apple answering about one request in ten with a spurious 401, now retried (see the spec).
