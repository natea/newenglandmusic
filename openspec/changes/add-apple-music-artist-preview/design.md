## Context

- **Built on the Spotify change:** `add-spotify-artist-preview` is implemented but not yet archived. It provides:
  - artist names (`core/artist_names.py`) and normalization (`core/artist_matching.py`);
  - a `spotify-artists` row in `event.html`, below the event's text;
  - `core/static/core/js/spotify_preview.js`, a delegated click handler that keeps one player open;
  - `SpotifyArtistLink`, `match_spotify_artists`, and the admin pattern this change repeats.
- **What was tested on 2026-10-27,** with Playwright's Chromium against Apple's live site, not signed in:
  - **The artist embed** (`embed.music.apple.com/us/artist/159260351`) rendered, but Play loaded no audio and changed nothing.
  - **The album embed** (`/us/album/1708308989`) started a 30-second preview (`audio-ssl.itunes.apple.com/.../AudioPreview...`) on Play.
  - **The song embed** (`/us/album/964625535?i=964625539`, The Ballroom Thieves' "Archers") showed a compact one-song player (cover, title, artist, Play, "View in Apple Music"), and started its preview on Play.
  - **A nonsense path** rendered a blank grey panel with a music note.
- **What the Apple Music API offers** ([documentation](https://developer.apple.com/documentation/applemusicapi)):
  - **Search:** `GET /v1/catalog/{storefront}/search?types=artists&term=…`.
  - **Artist views:** `GET /v1/catalog/{storefront}/artists/{id}/view/top-songs`, documented as "Songs associated with the artist based on popularity in the current storefront". Also `featured-albums` and `latest-release`.
  - **Authorization:** every request needs a developer token, an ES256 JWT signed with a MusicKit private key. Its `iss` is the team ID, its `kid` the key ID, and it expires at most 6 months after it's issued. Catalog requests need no user token.
  - **Rate limits:** over the limit, the API answers 429 until the rate drops. The limit itself isn't published.
- **The owner has an Apple Developer Program membership,** as of 2026-10-27.

## Goals / Non-Goals

**Goals:**
- A player that plays something for every visitor, not only Apple Music subscribers.
- The artist's most popular song, as Apple documents it, rather than a guess.
- Reuse the Spotify change's names, row, script and admin pattern.

**Non-Goals:**
- **Our own preview player built from preview URLs.** Apple's widget handles playback, branding and sign-in.
- **The free iTunes Search API.** Its order isn't documented, and the paid API is available.
- **Signing visitors in to Apple Music** (MusicKit JS user tokens). Full-song playback for subscribers comes from Apple's widget, through their own Apple Music sign-in.
- **Merging `SpotifyArtistLink` and `AppleMusicArtistLink`** into one model. That's worth doing if a third service arrives.

## Decisions

**1. Embed the top song, and link the artist page.**
- **Why:** the artist embed is the artist-level player, but signed-out visitors can't play it, and that's most visitors.
- **How it works:**
  - The song embed plays a preview for everyone.
  - It's compact, about the height of the Spotify player.
  - `top-songs` makes it the artist's most popular song.
  - The "More by <artist> on Apple Music" link under it gives the artist-level view.
- **Alternatives rejected:**
  - The artist embed: silent for signed-out visitors.
  - The album embed: it plays the album's first track, not the best-known one, and it's taller.
  - `latest-release`: it's empty for artists with nothing recent, and newest isn't the best introduction.

**2. The client: `core/apple_music.py`, with `requests` and `PyJWT`.**
- **The token:**
  - `developer_token()` signs an ES256 JWT, with `iss` the team ID, the header `kid` the key ID, `iat` now and `exp` one hour later.
  - It's cached in memory until five minutes before it expires.
  - An hour, rather than Apple's 6-month maximum, keeps a leaked token short-lived. The token is never stored or logged.
- **The private key:** `APPLE_MUSIC_PRIVATE_KEY` holds the `.p8` file's PEM text. Environment variables often turn newlines into `\n`, so the client converts them back.
- **Requests:**
  - `search_artists(name)` calls `/v1/catalog/us/search?types=artists&term=<name>&limit=10`, and returns `[{"id", "name"}]`.
  - `top_song(artist_id)` calls `/v1/catalog/us/artists/{id}/view/top-songs?limit=1`, and returns `{"song_id", "album_id"}` or `None`. The album ID comes from the song's `attributes.url` (`…/album/<slug>/<album id>?i=<song id>`). The song's `albums` relationship would cost another request.
  - `parse_artist_id(url)` handles `music.apple.com/<storefront>/artist/<slug>/<id>` URLs.
- **Retries:** requests are spaced 0.5 seconds apart. A 429 gets `Retry-After`, or else a backoff of 1, 2 and 4 seconds, for at most three tries. A 401 raises `AppleMusicAuthError`, which stops the run.
- **Errors:** messages carry Apple's `errors[].detail`, and never the token or key.

**3. Server-side matching in the daily job, like Spotify's.**
- **Why:** it gives editor review and overrides, and one search per name. The developer token also stays on the server.
- **The command:** `match_apple_music_artists` is a `RecordedCommand`, with `--names`, `--limit` and `--dry-run`, run in `bin/daily.sh` after `match_spotify_artists`. Daily, as with Spotify, so new events get buttons the next morning, and a run cut short by rate limits carries on the next day.

**4. A model, `AppleMusicArtistLink`, mirroring `SpotifyArtistLink`.**
- **Fields:** `name_key` (unique), `status`, `apple_artist_id`, `top_song_id`, `top_album_id`, `source`, `checked_at` and `last_seen_at`.
- **Refresh and expiry:** the 30-day rules are the same as Spotify's, with one difference: an editor's link has its top song refreshed, though never its artist. A top song changes as an artist releases music; the artist an editor chose doesn't.

**5. Rendering and script.**
- **Baking:** `bake_event_html` passes `artist_previews`, one entry per name, each with optional Spotify and Apple IDs. `event.html` renders both buttons in the existing row (renamed `artist-previews`).
- **The script:** `spotify_preview.js` becomes `artist_preview.js`, and handles `data-spotify-artist` and `data-apple-song`.
  - For Apple, it inserts the song iframe, then the "More by …" link.
  - Opening any player first removes every `.artist-player` element, so the one-player rule covers both services.
- **Iframe attributes:** the Apple iframe uses those of Apple's own embed code: `allow="autoplay *; encrypted-media *; fullscreen *; clipboard-write"`, `sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-storage-access-by-user-activation allow-top-navigation-by-user-activation"`, a height of 175, and `loading="lazy"`.

**6. When the buttons show.** Apple buttons render only when the three credentials are set and `APPLE_MUSIC_PREVIEWS` is `true`. Matching needs only the credentials, so links can be built and reviewed in the admin before visitors see any buttons.

**How Apple is mocked in tests.**
- **What's patched:** the client takes a session, sleep and clock, as the Spotify client does.
- **The key:** tests generate a throwaway P-256 key with `cryptography`, and verify the signed token with its public half. No real key is used.
- **Fixtures:** hand-written JSON in `core/tests/fixtures/apple_music/`, in the API's documented shapes, with no personal data:
  - search results for a unique match, two same-name artists and no exact match;
  - top songs with a result and empty;
  - a 429 and a 401.
- **The browser test:** `test_spotify_preview_browser.py` becomes `test_artist_preview_browser.py`, still aborting every request that isn't to the live server, and asserting the Apple iframe's `src` and the artist link.

## Risks / Trade-offs

- **[The rate limit isn't published]** → Space requests half a second apart, retry after 429, and run gradually with `--limit` if the first run hits limits.
- **[The private key in an environment variable]** → It's set only in `.env`, which is git-ignored, and in Render's dashboard. Tokens last an hour. If the key leaks, revoke it in the developer account and make a new one.
- **[A wrong match for a local band sharing a famous name]** → As with Spotify: unique exact matches only, editor overrides, and a source filter for review.
- **[Two buttons per artist crowd the row]** → The buttons are small marks with the name. If the row is too busy, a later tweak can show one name with two marks.
- **[Apple's terms for promotional use]** → The listing promotes the artist's show, and Apple's own unaltered widget promotes their music on the same page. See the open question.

## Migration Plan

1. **Create the credentials** (owner):
   - Under **Certificates, Identifiers & Profiles > Identifiers**, add a **Media ID**.
   - Under **Keys**, add a key with **Media Services (MusicKit, ShazamKit, Apple Music Feed)** enabled, configured with that Media ID.
   - Download the `.p8` file; Apple allows this only once. Note the key's ID, and the team ID from **Membership**.
2. Set `APPLE_MUSIC_TEAM_ID`, `APPLE_MUSIC_KEY_ID` and `APPLE_MUSIC_PRIVATE_KEY` in `.env`, and on Render's web service. Then run a blueprint sync for the cron jobs.
3. Deploy the migration, with `APPLE_MUSIC_PREVIEWS` off.
4. Run `match_apple_music_artists`, and review the automatic matches in the admin.
5. Set `APPLE_MUSIC_PREVIEWS=true`, and re-render the events (`resave_all_events`).

**Rollback:** turn the switch off and re-render the events.

## Open Questions

- **Is a concert listing an allowed promotional use?** Apple's media-services marketing terms are written for promoting store content. Someone should read them, or ask Apple, before the switch goes on publicly. That doesn't change what gets built.
