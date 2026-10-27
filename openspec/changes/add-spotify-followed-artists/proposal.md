## Why

The calendar lists thousands of shows, but a visitor has to scan all of them to find the bands they care about. Most listeners already keep that list in Spotify, as the artists they follow. If they connect Spotify, the site can show which of those artists have upcoming shows near them.

## What Changes

- **Connect Spotify:** a "Connect Spotify" link signs the visitor in with Spotify's Authorization Code flow with PKCE, asking only for the `user-follow-read` scope. It creates no account on this site. The Spotify tokens live in the visitor's server-side session.
- **Your artists page:** a new page at `/my-artists` lists upcoming approved events whose title or artists name an artist the visitor follows on Spotify.
- **"Near them" means the area the visitor has already chosen:**
  - The page applies the same Region, State and Metro Area filter as the events listing, read from the same `geo_filter` cookie, and offers the same form to change it.
  - It needs no ZIP code or browser location, and with no area chosen it covers the whole Northeast.
- **Disconnect:** a "Disconnect Spotify" button deletes the tokens and the followed-artist list from the session at once. That meets Spotify's rule that disconnecting must stop all use of the user's data.
- **No database of Spotify data:**
  - Followed artists are fetched from Spotify and kept in the session for at most an hour.
  - Nothing from Spotify is written to the site's own tables.
  - Matched artist names link back to the artist on Spotify, and the page credits Spotify as the source, as Spotify's terms require.
- **Configuration:** new settings `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` and `SPOTIFY_REDIRECT_URI`. The Connect link appears only when they are set.
- **Not included:** email or push alerts. Alerts would need site accounts and a stored copy of each user's followed artists. Spotify also no longer returns a user's email to development-mode apps. This is a follow-up proposal if the on-site page proves useful.

## Capabilities

### New Capabilities
- `spotify-followed-artists`: connecting and disconnecting a Spotify account, matching the visitor's followed artists against upcoming events, and showing the matches for the visitor's chosen area.

### Modified Capabilities
None. The page reuses the region, state and metro filter as `event-geo-filter` defines it, without changing that capability's requirements.

## Impact

- **Spotify's development mode:**
  - Spotify now lets a development-mode app serve only **5 users**, each added by email in the Spotify developer dashboard, and the app's owner must have Spotify Premium.
  - Opening it to everyone needs Spotify's extended quota, which Spotify reportedly grants only to registered businesses with about 250,000 monthly active users.
  - Until then, this feature is for the team. The page tells anyone else who tries to connect why it failed.
  - `design.md` lists three ways to offer the page to everyone without the cap: following artists on this site, a Last.fm import, or uploading Spotify's data export.
- **New code:**
  - a Spotify client module (OAuth, token refresh, paging through followed artists, retrying after 429);
  - views and URLs for connect, callback, disconnect and `/my-artists`;
  - a template and a nav link.
- **Dependencies:** none. It uses `requests`, which is already pinned.
- **Settings and docs:** the new environment variables go in `.env.example`, `render.yaml` (`sync: false`) and `PRODUCTION.md`. Each redirect URI must be registered in the Spotify dashboard: `https://newenglandmusic.onrender.com/spotify/callback` for production and `http://127.0.0.1:8001/spotify/callback` for local development (Spotify rejects `localhost`).
- **Tests:** they mock every Spotify HTTP call. No test touches the network.
