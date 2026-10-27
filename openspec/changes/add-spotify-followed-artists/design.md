## Context

- **Visitors have no accounts.** The site has no public login: Django auth is used only by the admin.
- **The area filter already exists.** The region, state and metro filter lives in `core/geo_filters.py`. `geo_filter_for_request(request)` reads it from the `region`, `state` and `metro` query parameters or the `geo_filter` cookie, and `core/templates/core/geo_filter_form.html` renders the form.
- **Sessions are server-side.** They use Django's default database engine, so the cookie holds only a session key. Production sets `SESSION_COOKIE_SECURE`.
- **Event names are free text.** `Event.title` and `Event.artists` are both free text. `artists` is filled for only about a quarter of events (784 of 2,942 locally), is sometimes junk ("Organization"), and often lists only the openers, with the headliner in the title. Matching therefore has to read both fields.
- **What Spotify allows (checked 2026-10-26):**
  - `GET /me/following?type=artist` is current, uses cursor paging with `limit` up to 50, and needs `user-follow-read`.
  - Development-mode apps are limited to 5 allow-listed users, and their owner must have Spotify Premium.
  - The Developer Terms forbid building databases of Spotify Content and storing it indefinitely, and require deleting a user's data when they disconnect.

## Goals / Non-Goals

**Goals:**
- Keep the smallest footprint that meets Spotify's terms: one scope, no stored Spotify data, and immediate deletion on disconnect.
- Reuse the existing area filter, so that "near me" means the same thing everywhere on the site.

**Non-Goals:**
- Site user accounts, email alerts, or remembering a visitor across browsers.
- Liked songs, top artists or playlists as sources of artists. Each needs another scope, so each is a later choice.
- Applying for Spotify's extended quota.

## Decisions

**1. Session-only connection, with no site accounts.**
- **How it works:** tokens and the cached artist list go in `request.session["spotify"]`.
- **Why:**
  - No new model is needed, and nothing has to be deleted later: disconnecting, or the session expiring, removes it all.
  - It also keeps the change small, while only five people can use it anyway.
- **Alternative rejected:** a `SpotifyAccount` model linked to a Django user, with stored tokens and artists. Alerts would need it, but it would add accounts, a stored database of users' Spotify data, and a deletion job. Defer it until alerts are wanted.

**2. Authorization Code flow with PKCE, using a confidential client.**
- **How it works:**
  - The server has a secret, so it does the code exchange with both the client secret (HTTP Basic) and the PKCE `code_verifier`.
  - The verifier and `state` are kept in the session between `/spotify/connect` and `/spotify/callback`.
  - Spotify's rules allow either flow for a backend. PKCE adds protection against a stolen code at no cost.
  - The Implicit Grant flow is deprecated and is not used.

**3. The redirect URI comes from settings, not the request.**
- **How it works:** `SPOTIFY_REDIRECT_URI` must exactly match a URI registered in the Spotify dashboard.
- **Why:** building it from `request.build_absolute_uri()` would break behind Render's proxy, and on `localhost`, which Spotify rejects. Locally, the setting is `http://127.0.0.1:8001/spotify/callback`.

**4. A small client module using `requests`, with no Spotify SDK.**
- **Where:** `core/spotify.py`, alongside the Ticketmaster and Eventbrite clients.
- **What it does:**
  - builds the authorize URL;
  - exchanges codes and refreshes tokens;
  - refreshes once on 401;
  - pages `/me/following` with the `after` cursor and `limit=50`, capped at 40 pages (2,000 artists);
  - on 429, sleeps for `Retry-After` (or an exponential delay of 1, 2 and 4 seconds), at most three tries.
- **Errors:** it raises typed errors (`SpotifyAuthError`, `SpotifyForbidden`, `SpotifyBusy`) carrying Spotify's `error.message`, which the view turns into the messages the spec requires. The token and the secret are never part of an exception message.
- **Alternative rejected:** `spotipy`, which brings its own token cache (written to a file by default) and is more than we need for two endpoints.

**5. What the session cache holds.** It stores `{id, name, url}` for each followed artist, plus `fetched_at`.
- **Why:** this is "temporary caching of metadata" for immediate use, which the terms allow, and refetching after an hour keeps it current.
- **Size:** the session is a database row, so 2,000 artists at about 80 bytes each comes to well under 200 KB.

**6. Match in Python against upcoming events.**
- **Where:** `core/artist_matching.py`, as `normalize(name)` and `event_matches(event, followed)`.
- **How it works:**
  - Load the upcoming approved events in the visitor's area. There are a few thousand at most, using `Event.objects` and the existing `area_q`.
  - Build a whole-phrase regex over each event's normalized title and artists text.
  - Normalization uses `unicodedata` NFKD to strip accents, replaces `&` with "and", drops punctuation and collapses whitespace.
  - Short single-word names use the exact-entry rule from the spec.
- **Alternative rejected:** doing this in Postgres with `unaccent` and regex. It would need an extension, and the logic is easier to test in Python.
- **Speed:** a few hundred followed names against about 2,000 events is fast enough for a page view. If profiling disagrees, precompute one normalized haystack per event.

**7. Reuse the area filter unchanged.**
- **How it works:** `/my-artists` calls `geo_filter_for_request`, applies the same cookie action as the index view, and includes `geo_filter_form.html`.
- **Why:** the page sees whatever area the visitor last chose on the listing, and choosing one here carries back to the listing. No ZIP code or geolocation is needed, because "near me" means the region, state or metro the visitor picked.

**8. Hide everything unless it's configured.**
- **How it works:** when `SPOTIFY_CLIENT_ID` or `SPOTIFY_CLIENT_SECRET` is unset, a context flag hides the nav link, and the views raise `Http404`.
- **Why:** the deployed site stays as it is until the keys are added in Render.

**How Spotify is mocked in tests.**
- **What's patched:** every outbound call goes through one `requests.Session` in `core/spotify.py`, and tests patch it with `unittest.mock`.
- **Canned responses:** the token endpoint, `/me/following` pages (including a 3-page cursor sequence), 401, 403, 429 with `Retry-After`, and `invalid_grant`.
- **Fixtures:** hand-written JSON in `core/tests/fixtures/spotify/`, with fake IDs and no real tokens.
- **No real waiting:** `time.sleep` is patched, so tests that hit 429 don't wait.
- **Offline:** the suite still passes with the network blocked.

## Risks / Trade-offs

- **[Only 5 Spotify users in development mode]** → Present it as a team preview. The 403 message tells anyone else why connecting failed. Opening it to the public needs extended quota, which may never be granted to a site this size, so this page should prove its worth before alerts or accounts are built on it.
- **[False matches on generic names]** (for example "Low" or "Live") → Whole-phrase matching, plus the exact-entry rule for short names. Remaining false matches are visible to the visitor and harmless, since it's their own page. If they're common, a later change can match on the Spotify artist IDs that `add-spotify-artist-preview` links to events.
- **[Missed matches]**, because the artist field is often empty or the headliner sits only in a free-text title → Matching on both fields covers most cases. Better artist extraction in `fetch_events` is a separate improvement.
- **[The session holds personal data until it expires]**, two weeks by default → Disconnect deletes it immediately, and the terms allow keeping it while the visitor is still connected. The refresh token is the sensitive part, and it never leaves the server.
- **[Spotify changes or removes `/me/following`]** → Spotify has moved other follow endpoints to `/me/library`. The client keeps the endpoint in one function, and the tests pin its response shape, so a move is a one-line change.

## Alternatives without the 5-user limit

The cap applies only to people who sign in with Spotify. If it rules this design out, any of these gives every visitor a "your artists" page. They can also be combined, with the Spotify connection kept as a team-only extra. Each would need its spec and tasks revised before it's built.

1. **Follow artists on this site** (recommended if the cap matters).
   - Visitors pick artists from the names on upcoming events, or paste in a list.
   - The list lives in the browser (a cookie or local storage), so there are no accounts.
   - Matching and the area filter work as in this design.
   - It needs no outside service, works for people who don't use Spotify, and sidesteps Spotify's data rules.
2. **Import from Last.fm.**
   - Last.fm's free API (`user.getTopArtists`) returns a public user's most-played artists from their username, with no sign-in and no user cap.
   - Many Spotify listeners log their listening there. It's a one-click import into option 1, and needs a Last.fm API key.
3. **Upload Spotify's "Download your data" export.**
   - Anyone can request their own data from Spotify (Account → Privacy); it arrives as a zip of JSON files a few days later.
   - Uploading `YourLibrary.json` needs no API and has no cap.
   - **Unverified:** no documentation says whether that file lists followed artists. Check a real export's keys before choosing this.

Not options, because they break Spotify's terms or no longer work:
- splitting users across several apps of 5 users each;
- scraping Spotify's website;
- reading other users' public profiles or playlists, which development mode removed.

## Migration Plan

1. Create a Spotify app in the developer dashboard, owned by an account with Premium.
2. Register both redirect URIs, and add the team's Spotify emails as users.
3. Set `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` and `SPOTIFY_REDIRECT_URI` locally in `.env`, and in Render's dashboard.
4. Deploy.

No database migration is needed. To roll back, unset the variables: the link and the pages disappear, and connected sessions simply stop being used.
