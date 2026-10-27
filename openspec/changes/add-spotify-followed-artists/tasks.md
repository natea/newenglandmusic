## 1. Settings and Spotify client

- [ ] 1.1 Add `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` and `SPOTIFY_REDIRECT_URI` to `nycnoise/settings/base.py` (blank by default), `.env.example`, and `render.yaml` (`sync: false`), plus a `spotify_enabled` template context flag. Verify that `manage.py check` passes with and without them set.
- [ ] 1.2 Write `core/spotify.py`. Verify it with the client tests in 1.3. It covers:
  - building the authorize URL, with a PKCE S256 challenge and `state`;
  - the code exchange and token refresh, with HTTP Basic client auth;
  - `followed_artists()`, which pages `/me/following?type=artist` with `after` and `limit=50`, capped at 40 pages;
  - one refresh-and-retry on 401;
  - on 429, a `Retry-After` wait with exponential backoff, for at most 3 tries;
  - the typed errors `SpotifyAuthError`, `SpotifyForbidden` and `SpotifyBusy`, which carry Spotify's error message and never a token or secret.
- [ ] 1.3 Add hand-written fixtures in `core/tests/fixtures/spotify/` (token responses, a 3-page followed-artists sequence, and 401, 403, 429 and `invalid_grant` bodies), and `core/tests/test_spotify_client.py`, which patches the module's HTTP session and `time.sleep`. Verify that the tests cover the PKCE URL parameters, paging through all 120 artists, refresh on 401, `invalid_grant`, waiting for `Retry-After`, three 429s raising `SpotifyBusy`, and that no secret appears in an exception's text. They must pass offline.

## 2. Artist matching

- [ ] 2.1 Write `core/artist_matching.py`, with `normalize()`, which handles case, accents, punctuation, "&" and a leading "The", and `matching_artists(event, followed)`, which matches whole phrases and applies the exact-entry rule to single words of three letters or fewer. Verify it with 2.2.
- [ ] 2.2 Add `core/tests/test_artist_matching.py`, covering each scenario in the matching requirement: the artists text, the title with "The" and case, whole words only ("Low" vs "Lowland Hum"), short names as whole entries ("Yes"), and accents and ampersands. Verify that it passes.

## 3. Connect, callback, disconnect

- [ ] 3.1 Add views and URLs for `spotify/connect`, `spotify/callback` and `spotify/disconnect` (POST with a CSRF token), which return 404 when Spotify isn't configured. Keep the PKCE verifier and `state` in the session. On callback, check `state`, handle `error=access_denied`, exchange the code, store the tokens under `session["spotify"]`, and redirect to `/my-artists`. Disconnect deletes `session["spotify"]`. Verify with 3.2.
- [ ] 3.2 Add `core/tests/test_spotify_connect.py`, covering:
  - the connect redirect's parameters;
  - a successful callback, which stores the tokens and redirects;
  - a mismatched `state`, which stores nothing and makes no token request;
  - `access_denied`;
  - the not-configured 404 and the hidden nav link;
  - that disconnect clears the session, with no Spotify call afterwards.

  Verify that it passes.

## 4. Your-artists page

- [ ] 4.1 Add the `/my-artists` view and template, and a nav link shown when `spotify_enabled`. The view:
  - applies `geo_filter_for_request` and its cookie action, and includes `geo_filter_form.html`;
  - lists upcoming approved events in that area that match the followed artists (cached in the session for an hour), grouped by date;
  - shows each match linked to `open.spotify.com/artist/<id>`, with a "Followed artists from Spotify" credit;
  - has empty, not-connected and error states (testers-only on 403, busy on `SpotifyBusy`, and a prompt to reconnect on `SpotifyAuthError`).

  Verify it by viewing the page locally with a connected tester account.
- [ ] 4.2 Add `core/tests/test_my_artists.py`. Verify that it passes. It covers:
  - matches in the chosen state only, with and without an area chosen;
  - past and unapproved events excluded;
  - the no-matches message, with a link that clears the filter;
  - the not-connected explanation;
  - the cached list reused within the hour, with no Spotify call, and refetched after it;
  - the 403 testers message;
  - repeated 429s showing the busy message with status 200;
  - the attribution links;
  - that no token or secret appears in the HTML;
  - that no table other than `django_session` gains Spotify data.

## 5. Docs and check

- [ ] 5.1 Add a "Spotify connection" section to `PRODUCTION.md`, covering creating the app (the owner needs Premium), the redirect URIs, adding testers (5 at most), the variables, and the 5-user limit. Add the variables to the `AGENTS.md` secrets list. Verify by reading the docs through.
- [ ] 5.2 Run the whole suite with outbound network blocked. Then, locally with a real tester account, connect, view matches for a chosen state, and disconnect. Verify that the tests pass and that the session row no longer holds Spotify data after disconnecting.
