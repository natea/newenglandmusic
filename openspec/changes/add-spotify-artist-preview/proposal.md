## Why

Most acts on the calendar are local or touring bands a visitor has never heard. One click to hear them, right in the listing, makes it easier to decide to go to a show. Spotify's embeddable artist player plays an artist's popular tracks without the visitor signing in: full tracks for logged-in Spotify users, and previews for everyone else.

## What Changes

- **Reading artist names from events:** a new step splits each upcoming music event's title and artists text into individual artist names. It splits on "w/", "+", "feat.", commas and similar separators, and drops boilerplate such as "Presents:", "TBA" and "Organization". It doesn't split on "&" or "and", which appear in band names.
- **Matching names to Spotify artists:** a new command, `match_spotify_artists`, looks up each name with Spotify's Search API, using the Client Credentials flow, so no user signs in. It links a name only when exactly one Spotify artist has the same normalized name. Ambiguous names and names with no match are recorded, so they aren't searched again every week.
- **Storing only what's needed:** for each name, the site stores the normalized name, the Spotify artist ID, a match status and a check date. It stores no other Spotify data: no names, images, genres or popularity.
  - Automatic matches are re-checked after 30 days.
  - Links for names with no upcoming event for 30 days are deleted.
  - This keeps the site within Spotify's rule against keeping databases of Spotify content.
- **A play button in the listing:** each linked artist gets a small "▶ artist name" button after the event's title line.
  - Clicking it opens Spotify's embedded artist player for that artist, inline in the listing.
  - No Spotify iframe or script loads until the click, so pages stay fast and Spotify sets no cookies on a page view.
  - Without JavaScript, the button is a plain link to the artist on Spotify.
- **Admin corrections:** in the admin, an editor can paste a Spotify artist link to set or fix a name's match, or mark it "no Spotify artist". Neither choice is overwritten by later runs.
- **Scheduling:** `match_spotify_artists` joins the weekly job (`bin/weekly.sh`). Links that change are re-rendered into each affected event's stored HTML.

## Capabilities

### New Capabilities
- `event-artist-names`: extracting individual artist names from an event's title and artists text.
- `spotify-artist-preview`: matching artist names to Spotify artists, storing and expiring those links, admin corrections, and the click-to-play embedded player in the events listing.

### Modified Capabilities
None. `job-run-history` already covers any `RecordedCommand`, so recording the new command adds no requirement there.

## Impact

- **New code:**
  - a model, `SpotifyArtistLink`, with a migration and an admin page;
  - `core/artist_names.py`;
  - the `match_spotify_artists` command, a `RecordedCommand`;
  - a Client Credentials and Search addition to `core/spotify.py`. That module is shared with `add-spotify-followed-artists`; whichever change lands first creates it.
  - an `event.html` change, a small script and styles.
- **Spotify API usage:**
  - Client Credentials needs no user and isn't subject to the 5-user cap of development mode, but the app's owner still needs Spotify Premium.
  - Search returns at most 10 results per call in development mode, which is enough for exact-name matching.
  - The first run makes about one search per distinct name, roughly 1,000 to 2,000. Later weekly runs search only new names and expired matches. It's free; the client throttles itself and retries after 429.
- **Terms:**
  - The embed is a Spotify Widget, governed by Spotify's Widget Terms, and carries Spotify's own branding.
  - The fallback link goes back to Spotify, as the Developer Policy requires.
- **Settings:** it uses the same `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` as the followed-artists change. With them unset, the command exits without doing anything, and no buttons render.
- **Tests:** they mock every Spotify call, with hand-written search fixtures.
