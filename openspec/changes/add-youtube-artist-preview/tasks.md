## 1. Clients

- [x] 1.1 Add `core/youtube.py`:
  - a `YouTube` client with an injectable session, sleep and clock;
  - the key sent only in `X-goog-api-key`;
  - `search_videos(query)`, `videos(ids)` and `channels(ids)`;
  - back-off on 429 and 5xx, and a `QuotaExceeded` error for 403 `quotaExceeded` / `dailyLimitExceeded`;
  - error messages built from the response's reasons only.
  
  Verify with unit tests that cover the key header and its absence from URLs and errors, the back-off, and quota detection.
- [x] 1.2 Add `core/music_ids.py`:
  - Wikidata SPARQL by Spotify ID and Apple ID, batched and sent by POST;
  - MusicBrainz lookup from the Spotify URL to the artist's YouTube channel links, one request a second, with the site's user agent.
  
  Verify with fixture tests: Dinosaur Jr.'s Wikidata link, a MusicBrainz link, no link, and the pacing with an injected clock.
- [x] 1.3 Extend `AppleMusic.top_song()` to also return the song and album names from its existing response. Verify that the existing Apple tests still pass and that a new test reads the names.

## 2. Model and matching

- [x] 2.1 Add `YouTubeArtistLink`, with status, evidence, source, `channel_id`, `video_id`, `checked_at` and `last_seen_at`, and its migration. Verify that `makemigrations --check` is clean and that the migration applies.
- [x] 2.2 Add `core/youtube_links.py`. It holds:
  - the confirmation rules: the channel title equals the name, or the name plus " - Topic"; a Topic video's description has the song · artist line and the album; otherwise the video title contains the song; and the video can be embedded;
  - the evidence ladder;
  - the 30-day refresh and expiry;
  - re-rendering the affected events.
  
  Verify with tests for:
  - the Topic recording, the same-name band, the cover upload, a non-embeddable video, and sources that disagree;
  - a Spotify-only artist with no ID link;
  - refresh keeping a live video, a removed video being re-matched, and expiry;
  - the stored fields holding IDs only.
- [x] 2.3 Add the `match_youtube_artists` command (`RecordedCommand`), with `--limit` (default 90), `--dry-run` and the job summary counts. Verify with tests for:
  - not configured;
  - an unmatched name skipped;
  - the dry run;
  - the limit reached;
  - the quota exhausted mid-run, keeping and re-rendering what was found.

## 3. Admin

- [x] 3.1 Register `YouTubeArtistLink` in the admin, with filters by status, evidence and source. Add a form field for a channel or video URL, a "no YouTube" action, and a re-render on save. Verify with admin tests for:
  - pasting a video URL, including the `youtu.be` form;
  - pasting a channel URL;
  - rejecting a Spotify URL;
  - marking a name as "no YouTube";
  - an editor's match showing a button without a Spotify or Apple match.

## 4. Listing and player

- [x] 4.1 Add the YouTube button to the play-button row in `core/templates/core/event.html` (the row is baked into each event's stored html; `core/artist_previews.py` gives it the matches), behind `YOUTUBE_PREVIEWS`, using the same markup pattern and inline mark as the Apple button. Verify with render tests for:
  - the buttons beside Spotify and Apple Music;
  - the video and channel hrefs;
  - no YouTube URL in the page apart from the links;
  - the switch turned off.
- [x] 4.2 Add `youtubePlayer()` to `core/static/core/js/artist_preview.js`, using a `youtube-nocookie.com` iframe, the uploads playlist for channel-only matches, and 16:9 at no less than 200 × 200 px, with no autoplay. It shares the existing one-player-at-a-time logic. Verify with Playwright tests on `BrowserTestCase` for:
  - no player before a click;
  - the video src;
  - the channel playlist src;
  - the size;
  - one player across services;
  - removal on a second click.

## 5. Privacy page

- [x] 5.1 Add `/privacy`, with:
  - the YouTube API Services statement;
  - links to the Google Privacy Policy and YouTube's Terms of Service;
  - the saved-shows cookie;
  - a footer link on every page.
  
  Verify with render tests for the page's content and for the footer link.

## 6. Configuration and jobs

- [x] 6.1 Add `YOUTUBE_API_KEY` and `YOUTUBE_PREVIEWS` to settings, `.env.example`, `render.yaml` (the web service and the daily cron) and AGENTS.md. Add `match_youtube_artists --limit 90` as the last step of `bin/daily.sh`, and update `DAILY` in `core/tests/test_scheduled_jobs.py`. Verify that the scheduled-jobs tests pass with seven daily steps.
- [x] 6.2 Document the step, its quota and the key in PRODUCTION.md, and add the YouTube privacy-policy item to its launch checklist. Verify by reading the docs.

## 7. Check

- [x] 7.1 Run the whole suite with outbound network blocked. Then, with the user's approval of the key, run `match_youtube_artists --dry-run --limit 10` locally, and check each proposed match by hand on YouTube. Verify that the tests pass and that every proposed match is the right artist.
