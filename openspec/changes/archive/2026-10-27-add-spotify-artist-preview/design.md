## Context

- **Artist names are free text.** Events have a free-text `title` and `artists` (see `add-spotify-followed-artists`' design for how sparse and noisy `artists` is). Sample bills include "SHEBAD w/ Psymon Spine + A Halloween Surprise" and "State Theatre Presents: The Ballroom Thieves".
- **Event HTML is stored.** `core/utils_event_caching.bake_event_html` renders each event's HTML into `Event.baked_html_template`. So anything new in an event's markup must be rendered when the event is saved, and again whenever its inputs change.
- **The title line is a link.** `event.html` wraps the title and artists in the event's hyperlink. A button can't sit inside an `<a>`, and the text after it is already crowded with the ICAL, GCAL and MAP links. So the play buttons go in a row of their own below the text, not inside it.
- **The map clones events.** The day maps' info panel (`map.html`) shows copies of event elements.
- **Events have a kind.** `Event.kind` with `is_music_kind()` already says which events are music.
- **What Spotify allows (checked 2026-10-26):**
  - **Search:** `GET /search` with `type=artist` takes a `limit` of at most 10 in development mode. Artist objects no longer carry `popularity` or `followers` there, so a match can't be broken by popularity.
  - **Removed endpoint:** `GET /artists/{id}/top-tracks` is removed for development-mode apps.
  - **Embed:** the artist embed `open.spotify.com/embed/artist/<id>` needs no API call or authentication.

## Goals / Non-Goals

**Goals:**
- Show a play button only when the match is very likely right: a link to the wrong band is worse than no button.
- Store as little as possible: a name-to-ID map, with expiry.

**Non-Goals:**
- Choosing between same-name artists automatically by genre or location. An editor fixes those.
- Other services (Bandcamp, YouTube), or 30-second previews played by our own audio player.
- Rewriting how `fetch_events` extracts artists.

## Decisions

**1. Split names in a pure function, `core/artist_names.py: event_artist_names(event) -> list[str]`.**
- **How it works:** the rules are as the `event-artist-names` spec gives them. It's one ordered list of regex separators, a prefix stripper and a stoplist, which makes it easy to extend from real misses.
- **Shared code:** `normalize()` comes from `core/artist_matching.py`, which `add-spotify-followed-artists` adds. Whichever change lands first creates it, and both use the same normalization.

**2. Match only on a unique exact normalized name.**
- **Why:** with popularity gone, the only reliable signal in the search results is the name.
  - Exactly one exact match is accepted.
  - Two or more same-name results are marked ambiguous, for an editor to settle.
- **Known risk:** a local band that shares its name with a single, different Spotify artist will be matched wrongly. Editors can correct it, and the admin's "automatic" filter makes those links easy to review.
- **Alternative rejected:** taking the top search result. It's often a famous artist with a similar name.

**3. A model, `SpotifyArtistLink`.**
- **Fields:**
  - `name_key`, unique: the normalized name;
  - `status`, one of matched, ambiguous, not_found or none;
  - `spotify_artist_id`, nullable;
  - `source`, auto or editor;
  - `checked_at`;
  - `last_seen_at`, the last time an upcoming event named it.
- **Why a separate model:** keyed by the name, not the event, so one search serves every event that names an artist, and editors fix a name once.
- **What's not stored:** Spotify's display name. The button shows the name as written on our event.

**4. Expiry follows Spotify's "don't store indefinitely" rule.**
- **When it runs:** each run first updates `last_seen_at` for every name on an upcoming approved music event.
- **What it deletes:** links whose `last_seen_at` is more than 30 days old.
- **What it re-checks:** automatic links whose `checked_at` is more than 30 days old.
- **Why 30 days:** it matches the refresh window already used for Google Places coordinates, so both outside sources expire the same way.

**5. Rendering.**
- **What's rendered:**
  - `bake_event_html` passes `spotify_artists`: an ordered list of `(display name, artist ID)` for the event's matched names, looked up in one query by `name_key`.
  - `event.html` renders a `<div class="spotify-artists">` holding one `<a class="spotify-play" href="https://open.spotify.com/artist/<id>" data-spotify-artist="<id>" target="_blank" rel="noopener">` per artist. It goes after `.event-time-and-content` and `.event-ticket`, as a third child of the `.event` flex row.
  - `.event` gets `flex-wrap: wrap`, and the row takes the full width (`flex-basis: 100%`), indented to line up with the text past the time column. The time, text and tix columns don't change.
- **The script:** a small one (`static/js/spotify_preview.js`) listens for clicks on `document`, so it also works for the copies in the map panel. On a click it:
  - calls `preventDefault`;
  - removes any open player;
  - inserts `<iframe src="https://open.spotify.com/embed/artist/<id>" width="100%" height="152" frameborder="0" allowfullscreen loading="lazy" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture">` below the row of buttons, inside the event. The attributes are those of Spotify's [Creating an Embed](https://developer.spotify.com/documentation/embeds/tutorials/creating-an-embed) guide, which lists artists among the embeddable types, at its compact height.
  - The Widget Terms require showing the player as Spotify makes it, unaltered and not covered by anything, so the styles touch only its margins and corner radius.
- **When there's no ID:** with Spotify unconfigured, or no matched names, the list is empty and nothing renders.

**6. Re-render only what changed.**
- **Why:** event HTML is stored, and re-rendering all of it is slow.
- **How it works:**
  - The command collects the `name_key`s whose status or ID changed in this run.
  - It finds the upcoming events that name them by running `event_artist_names` over the upcoming events it has already loaded.
  - It calls `rebake_html()` and `queryset.update()` for each, rather than `Event.save()`, so nothing else on the event changes.
- **Admin edits:** saving a link in the admin does the same for that one name.

**7. The command.**
- **What it is:** `match_spotify_artists`, a `RecordedCommand` with `--dry-run`, `--limit N` and `--names "A,B"`.
- **What it does:** it gets a Client Credentials token, and spaces searches 0.5 seconds apart.
- **Retries:** it uses the same 429 handling as the shared client: `Retry-After`, then a backoff of 1, 2 and 4 seconds, at most three tries.
- **Its summary:** the job summary carries the counts from the spec.
- **Where it runs:** at the end of `bin/daily.sh`, after `fetch_events`, with `--limit 1000`. It was weekly at first. A real run on 2026-10-27 got the app blocked for about a day after 650 searches, so it moved to daily: a blocked run stops and keeps what it found, and the next morning's carries on, so a backlog clears itself.

**How Spotify is mocked in tests.**
- **What's patched:** the HTTP session of `core/spotify.py`, with `unittest.mock`, as in the followed-artists change, along with `time.sleep`.
- **Fixtures:** in `core/tests/fixtures/spotify/`:
  - `token_client_credentials.json`;
  - search results with one unique exact match, two same-name artists, no exact match, and a 429 with `Retry-After`.
- **Fake data:** the fixtures use fake artist IDs.
- **Server-side tests:** they check the rendered HTML: the link, the data attribute, and that no iframe is present.
- **Click scenarios:** they get one browser test, `core/tests/test_spotify_preview_browser.py`. It is a `StaticLiveServerTestCase` driven by Playwright for Python, added as a development dependency. The test:
  - aborts every request that isn't to the live server (`page.route("**/*")`), so it stays offline;
  - checks the iframe's `src` attribute, not its contents.

  If Chromium isn't installed, the test fails with a message naming `playwright install chromium`. It doesn't skip, because a skipped test isn't a passing one. CI installs the browser.

## Risks / Trade-offs

- **[A wrong band linked when names collide]** → Accept only unique exact matches, let editors override, and offer an admin filter for automatic links to review. Visitors see the Spotify player's artist name before anything plays, so a mismatch is visible.
- **[Playwright is a new dev dependency]**, and the suite's first browser test → It's the only way to cover the click scenarios automatically, as the project requires. It's limited to one test module, it runs offline, and the CI job gains a `playwright install --with-deps chromium` step. The alternative, verifying by hand as `add-event-music-filter` did for model-judgment scenarios, is weaker here, because click behavior is deterministic and testable.
- **[Spotify policy wording on storing IDs]** → The terms don't address IDs specifically. Storing only IDs, with 30-day expiry and no other metadata, is the narrowest reading. If Spotify objects, deleting the table removes all buttons and changes nothing else.
- **[The first run is slow, and Spotify's limits aren't published]** → About 2,500 names at 2 seconds each is roughly 85 minutes. The daily `--limit 1000` spreads it over three mornings, and a block only delays the rest by a day.
- **[The embed adds third-party content to the site]** → It loads only on click, and the player is Spotify's own branded widget, governed by the Widget Terms.

## Migration Plan

1. Deploy the migration.
2. Set the Spotify variables, shared with `add-spotify-followed-artists`.
3. Run `match_spotify_artists --dry-run --limit 50` locally to check matches, then a full run against the Render database.
4. The daily job keeps the links current from then on.

**Rollback:** unset the variables and re-render the events, or drop the table with a reverse migration. The listing then renders exactly as before.
