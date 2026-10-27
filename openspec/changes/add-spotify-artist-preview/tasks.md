## 1. Artist names

- [x] 1.1 Create `core/artist_matching.py` with `normalize()`, if `add-spotify-followed-artists` hasn't already. Write `core/artist_names.py: event_artist_names(event)`, with the separators, title prefixes, title stopwords, placeholder stoplist and music-only rule from the `event-artist-names` spec. Verify it with 1.2.
- [x] 1.2 Add `core/tests/test_artist_names.py`, covering every `event-artist-names` scenario: a comma-separated bill, featuring and with, a kept ampersand, a headliner only in the title, a presenter prefix, a tribute title, placeholders and a non-music event. Verify that it passes.

## 2. Model and admin

- [x] 2.1 Add the `SpotifyArtistLink` model, with `name_key` (unique), `status`, `spotify_artist_id`, `source`, `checked_at` and `last_seen_at`, and its migration. Verify that `makemigrations --check` is clean after the migration is added.
- [x] 2.2 Add an admin page for it. It has status and source filters, a field that accepts a Spotify artist URL or URI and parses it to an ID, and a "no Spotify artist" action. Both set the source to editor. Saving re-renders the upcoming events that name the link. Verify with 2.3.
- [x] 2.3 Add `core/tests/test_admin_spotify_link.py`, covering the scenarios: an editor fixing a wrong match (a URL with `?si=` parsed to its ID, and the event's HTML re-rendered with the new ID), marking no artist, and an invalid URL rejected. Verify that it passes.

## 3. Matching command

- [x] 3.1 Add Client Credentials token and `search_artists(name)` to `core/spotify.py`, creating the module if the other change hasn't. Use `type=artist` and `limit=10`, keep 0.5 seconds between requests, and handle 429 with `Retry-After` and backoff for at most three tries. Add fixtures to `core/tests/fixtures/spotify/`: a client-credentials token, a unique match, same-name artists, no exact match and a 429. Verify with 3.3.
- [x] 3.2 Write the `match_spotify_artists` `RecordedCommand`. Verify with 3.3. It:
  - collects names from upcoming approved music events, and updates `last_seen_at`;
  - deletes links unseen for more than 30 days;
  - searches new names and automatic links checked more than 30 days ago, skipping editor-set ones;
  - records matched, ambiguous or not found;
  - re-renders the affected events with `queryset.update()`;
  - supports `--dry-run`, `--limit` and `--names`;
  - exits 0 without doing anything when Spotify isn't configured;
  - sets `job_summary` to the counts.
- [x] 3.3 Add `core/tests/test_match_spotify_artists.py`, covering:
  - the matching scenarios: a unique match, two same-name artists, no exact match, one search for a name on several events, not configured, and a dry run;
  - the storage scenarios: a stale match re-checked, an unneeded link deleted, and no extra Spotify fields stored;
  - the throttling scenarios: rate limited then succeeding, a persistent failure leaving the link unchanged, and the job summary counts.

  It patches the HTTP session and `time.sleep`. Verify that it passes offline.

## 4. Listing button and player

- [x] 4.1 In `bake_event_html`, pass the event's matched `(display name, ID)` pairs. In `event.html`, render a `spotify-play` link for each in a `spotify-artists` row of its own below the event's text, outside the text with the ICAL, GCAL and MAP links. Add `static/js/spotify_preview.js`, which uses a delegated click handler, keeps one player at a time and toggles it off on a second click. Add styles in the SCSS. Include the script on the pages that list events. Verify with 4.2 and 4.3.
- [x] 4.2 Add `core/tests/test_spotify_preview_render.py`. Verify that it passes. It checks that:
  - a matched artist gets a button, and an unmatched one doesn't;
  - the button's link and label are right;
  - the homepage has no `open.spotify.com` iframe;
  - nothing renders when Spotify isn't configured.
- [x] 4.3 Add `playwright` to the development requirements with `uv pip install`, add `playwright install --with-deps chromium` to `.github/workflows/django.yml`, and write `core/tests/test_spotify_preview_browser.py`. It's a `StaticLiveServerTestCase` that aborts every request that isn't to the live server. Verify that it passes locally and in CI. It covers:
  - a click opening the player with the right `src`;
  - one player at a time;
  - a second click closing the player;
  - a link that points to Spotify when JavaScript is off.

## 5. Scheduling, docs and check

- [x] 5.1 Add `step python manage.py match_spotify_artists --limit 1000` to `bin/daily.sh`, after `fetch_events` (moved from the weekly job after a real run hit Spotify's rate limit). Document the command, the expiry rules and how editors correct matches in `PRODUCTION.md` and the `AGENTS.md` pipeline list. Verify that `bash -n bin/daily.sh` passes, and by reading the docs.
- [x] 5.2 Run the whole suite with outbound network blocked. Then run `match_spotify_artists --dry-run --limit 50` against the local database, with real credentials, and spot-check 20 matches. Write the output to `logs/match_spotify_artists-YYYY-MM-DD.log`. Verify that the tests pass and that the spot-checked matches are right, or note the wrong ones as rule fixes before the full run.
