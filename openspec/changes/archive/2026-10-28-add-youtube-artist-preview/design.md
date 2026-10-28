## Context

- **The existing play buttons:**
  - `SpotifyArtistLink` and `AppleMusicArtistLink` key each artist name by `core.artist_matching.normalize()`;
  - they keep only IDs, refresh after 30 days, and expire 30 days after no event names them;
  - `core/artist_previews.py` gives `core/templates/core/event.html` the buttons, which are baked into each event's stored html, so a changed link re-renders the events that name it;
  - `core/static/core/js/artist_preview.js` inserts one player at a time on click.
- **What's already established:**
  - a Spotify or Apple match means a unique exact-name artist in that catalog, or an editor's choice;
  - Apple matches also record the artist's top song.
- **What YouTube offers (Data API v3, measured or read 2026-10-28):**
  - quota: 10,000 free units a day; `search.list` costs 100, while `videos.list` and `channels.list` cost 1 for up to 50 IDs;
  - the API has no field for the "Official Artist Channel" badge, and no channel links;
  - "Topic" channels, titled "<artist> - Topic", are made by YouTube from distributors' releases. Their videos' descriptions follow a fixed form: "Provided to YouTube by <distributor>", then "<song> · <artist>", the album, and "℗" lines;
  - Spotify's and Apple's APIs don't link to YouTube.
- **The terms:**
  - from the Developer Policies: stored API data must be deleted or refreshed within 30 days; a privacy policy must mention YouTube API Services and link to Google's Privacy Policy; the client must link to YouTube's Terms;
  - from Required Minimum Functionality: no changes to the player beyond its API documentation, no overlays, and a viewport of at least 200 × 200 px.

## Goals / Non-Goals

**Goals:**
- Show a YouTube button only when evidence ties the YouTube music to the artist already matched on Spotify or Apple Music.
- Stay within the free quota, with no billing.

**Non-Goals:**
- Matching artists that aren't matched on Spotify or Apple Music, except by an editor.
- Searching Spotify for top tracks to confirm Spotify-only artists. Spotify's daily allowance is already the bottleneck (see PRODUCTION.md). This can come later.
- A custom-skinned player.
- Following or recommending videos beyond the one played.

## Decisions

**1. Evidence ladder, cheapest and strongest first.**
- **Steps:**
  1. **ID links:** Wikidata (Spotify ID P1902, or Apple Music ID P2850, to YouTube channel P2397) and MusicBrainz (Spotify URL to artist, then its `youtube.com/channel/` links). These are free, and are links between IDs that people curate, not name guesses.
  2. **Top-song recording:** one `search.list`, then one `videos.list` for full descriptions and embeddable status. We need `videos.list` because search snippets truncate descriptions.
- **Why this is sure enough:** a different act with the same name would also need a song with the same name, and for Topic videos an album with the same name. Fan uploads and covers fail the channel test.
- **Every match is checked:** a found channel or video is always read through the API (1 unit) before it's recorded, so a deleted channel from a stale Wikidata entry gets no button.
- **Alternatives rejected:**
  - name-only channel search (`type=channel`): same-name artists are the whole problem;
  - the "Official Artist Channel" badge: it isn't in the API, and scraping it would break the terms;
  - comparing channel descriptions with websites: we don't hold artist websites.

**2. A channel-only match plays the channel's uploads playlist.** The uploads playlist is the channel ID with "UC" replaced by "UU", embedded as `embed/videoseries?list=UU…`. It needs no extra quota. A Topic channel's uploads are all songs. An artist channel's may include vlogs, which is acceptable because they're the artist's own. When the name also has an Apple top song, we could spend a search to pick that song's video inside the channel (`search.list` with `channelId`). We don't, to save quota. Revisit if the playlists turn out poor.

**3. Model and command mirror the Apple Music ones.**
- **`YouTubeArtistLink`:**
  - `name_key` (unique), `status` (matched, ambiguous, not found, none) and `evidence` (wikidata, musicbrainz, topic-song, channel-song, editor);
  - `channel_id` and `video_id` (blank for channel-only matches), `source` (auto or editor), and `checked_at` and `last_seen_at`.
- **`match_youtube_artists`:**
  - reuses the Apple and Spotify links' names;
  - re-renders events through the same helper `core/spotify_links.py` uses;
  - records a `JobRun` via `RecordedCommand`.
- **Apple Music:** `AppleMusic.top_song()` also returns `name` and `album_name` from the response it already gets. Those are passed to the YouTube step in memory, so the Apple command's stored data doesn't change. The YouTube command calls `top_song()` itself for names it searches. That's one Apple request, which Apple's allowance easily covers, so it needn't depend on the order of the steps.

**4. The player is a plain iframe, made on click.**
- **The iframe:** `artist_preview.js` gains a `youtubePlayer(button)` beside `applePlayer` and `spotifyPlayer`. It makes an `<iframe src="https://www.youtube-nocookie.com/embed/…">` with `allow="encrypted-media; picture-in-picture; fullscreen"`, `referrerpolicy="strict-origin-when-cross-origin"`, and CSS `aspect-ratio: 16/9; width: 100%; min-width: 200px; min-height: 200px`.
- **Why no IFrame API:** we don't need it. A plain iframe loads no YouTube script before a click, and it is the player as documented.
- **Why the referrer policy:** Required Minimum Functionality wants clients to identify themselves through the Referer header.
- **Alternative rejected:** pixelgridui/youTube-player and csPlayer. Both hide YouTube's controls and draw their own, which RMF forbids.

**5. Key handling.** `requests` with `headers={"X-goog-api-key": key}`. Error messages are built from the response's `error.errors[].reason` only, never from the request URL or headers. That's the same pattern as `core/apple_music.py`'s `error_message`.

**6. The privacy page.** It's a static template at `/privacy`, with a footer link. It also covers the saved-shows cookie, so the page helps the launch checklist generally.

**How it's tested.** Nothing reaches the network, and the suite passes with outbound requests blocked.
- **YouTube Data API:**
  - `core.youtube.YouTube` takes an injectable `session`; tests pass a fake session that answers `search` and `videos` / `channels` with recorded JSON fixtures in `core/tests/fixtures/youtube/`, with keys stripped;
  - the fake session asserts the key is in the `X-goog-api-key` header and not in the URL;
  - `sleep` is injected, so back-off tests don't wait;
  - the fixtures cover a Topic-channel result, a same-name band, a cover upload, a non-embeddable video, and a 403 `quotaExceeded` response.
- **Wikidata and MusicBrainz:** `core.music_ids` takes the same injectable session, with recorded SPARQL and MusicBrainz JSON fixtures, including the Dinosaur Jr. example and two sources that disagree. The one-request-a-second MusicBrainz pacing is checked with an injected clock.
- **Apple Music:** `top_song()` is patched to return IDs and names, as the existing Apple tests do.
- **The listing and player:**
  - render tests check the buttons' hrefs and data attributes, that no YouTube URL appears before a click, and the `YOUTUBE_PREVIEWS` switch;
  - Playwright tests on `core/tests/browser.py` (`BrowserTestCase`, which aborts every request that isn't to the test server) click the button and check the iframe's src and size, that only one player is open, and removal on a second click. The iframe's own request is aborted, so nothing is fetched from YouTube.
- **The daily job:** `core/tests/test_scheduled_jobs.py`'s `DAILY` list gains the new step.
- **CI compiles the SCSS before the tests** (`.github/workflows/django.yml`). The compiled css is git-ignored, and tests run with the processor off, so without this step the browser test of the player's 200 px minimum would see unstyled iframes.

## Risks / Trade-offs

- **[Low coverage at first]** → Only confirmed matches show buttons. That's the user's requirement. The admin's not-found filter lets editors add the artists they care about.
- **[A Topic channel shared by two acts]** → YouTube sometimes merges same-name artists into one Topic channel. Requiring the song and album lines in the description guards the video we play. For a channel-only playlist from Wikidata or MusicBrainz, the ID link itself is the evidence.
- **[Wikidata or MusicBrainz errors]** → Both are community-edited. A wrong entry gives a wrong button. Editors can mark a name "no YouTube", and the 30-day API check drops dead channels.
- **[Quota]** → 90 searches a day clears about 115 Apple-matched names in two days, then new names trickle in. Quota errors stop the run cleanly, as Spotify blocks do.
- **[Terms: the privacy policy]** → The policies also say users must agree to the privacy policy "before" using the client. For a public listing, the footer link plus the statement on the page is the usual reading, but it's a judgment. Add it to PRODUCTION.md's launch checklist, beside the open Google Places map question, and keep the site unshared until both are settled.
- **[Embeds that are blocked in some regions, or age-restricted]** → The player shows YouTube's own message. The refresh drops videos that are no longer embeddable.

- **[MusicBrainz busy]** → On 2026-10-28 it answered 503 to every request for a while, whatever the user agent. Busy requests are retried with back-off, and then the run goes without it. Wikidata and the song search still work, and the names are checked again in 30 days.
- **[A key restricted to websites]** → The first key tried (2026-10-28) had a website (HTTP referrer) restriction. Google refuses such a key from a server with 403 `forbidden`. So the command stops at the first refusal, rather than failing every name, and PRODUCTION.md says to set the restriction to None or to IP addresses.

## Migration Plan

1. Create a Google Cloud API key restricted to the YouTube Data API v3. Set `YOUTUBE_API_KEY` in `.env`, and on Render only after the user approves writing it there.
2. Deploy the migration and code, with `YOUTUBE_PREVIEWS` off.
3. Run `match_youtube_artists --dry-run --limit 10` locally, and check each match by hand.
4. Turn `YOUTUBE_PREVIEWS` on, and run `resave_all_events`.

**Rollback:** set `YOUTUBE_PREVIEWS` off and re-save the events. The buttons disappear, and the links stay.

## Open Questions

- After the first week, measure how many matches come from each kind of evidence. That decides whether picking a song inside channel-only matches (decision 2) is worth its quota.
