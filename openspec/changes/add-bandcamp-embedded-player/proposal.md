Issue: [#47 Embedded Bandcamp player on event listings, artist and band pages, and the discovery deck](https://github.com/natea/newenglandmusic/issues/47)

Issue: [#47 Embedded Bandcamp player on event listings, artist and band pages, and the discovery deck](https://github.com/natea/newenglandmusic/issues/47)

## Why

Acts that have a Bandcamp page are often small acts with no Spotify, Apple Music or YouTube presence, so the listing's play buttons give nothing for them. Bandcamp's own embedded player would let a visitor hear them, and sends listeners to Bandcamp. The player needs a numeric album or track ID, which the site doesn't have: it keeps only the act's page address. The owner decided on 11 November 2026 that fetching an act's Bandcamp page once to read that ID is acceptable use, which replaces the current rule that nothing is ever requested from Bandcamp.

## What Changes

- **A record keeps its Bandcamp player:** the kind (album or track) and ID, when it was last looked up, a status (found, no playable release, blocked, gone, unreadable, failed) and the Bandcamp address it was read from. An editor can set or clear the player in the admin, which makes it usable at once; an editor's value is never overwritten by the lookup. A failed refresh never hides a player that was found.
- **A new command, `find_bandcamp_embeds`,** fetches each act's Bandcamp page once (robots.txt obeyed, the honest user agent, about two seconds between requests, no proxies) and reads the ID of a release the player can play:
  - a page that redirects to a featured release gives it from the release's structured data (the `albumRelease` item ID, or the page properties for a track);
  - a discography grid gives it from the first music tile (`data-item-id="album-…"` or `"track-…"`);
  - merchandise tiles are skipped, and a release whose player says it is not available (for example a physical-only release) is skipped for the next release, up to three tried.
- **Rarely refreshed, never on a page view:** an act is looked up once; one with a player is looked up again only after a year, one with "no playable release" after 90 days, and one whose Bandcamp address changes at the next run. Visitors never trigger a request to Bandcamp from the server.
- **The player on three screens:**
  - event listings: a Bandcamp button beside the existing play buttons, last in their order (Spotify, Apple Music, YouTube, Bandcamp as the row stands today), opening Bandcamp's player below the row only when clicked;
  - artist and band pages: the player shown on the page, loaded only when the visitor presses play;
  - the discovery deck from #26, as the last player in its order, unless decided otherwise. That deck is not in the codebase yet, so this change only fixes the rule it follows (open question in the design).
- **Weekly job:** the command runs in `bin/weekly.sh`, last, and is recorded as a `JobRun`. A run looks up at most 100 acts unless `--limit` says otherwise.
- **Listings stay current:** event listings are re-rendered whenever an editor's change, a review mark, a performer link rebuild or a deletion alters an act's button, and the Bandcamp button shows even when no other player service is switched on.
- **The rule is rewritten** in AGENTS.md, PRODUCT.md, `core/artists.py` and the artist-records spec (PRODUCTION.md only documents the new command): Bandcamp may be requested only to read a player ID from an act's own page, by this command, and never scraped for anything else.

### Not in this change

- Scraping anything else from Bandcamp (titles, artwork, bios, tracklists, prices, merch), or any proxy or scraping service.
- Finding an act's Bandcamp page when it has none; that stays with the import, MusicBrainz, the link hub and editors.
- Choosing a release by taste: the first playable release the page offers is used.
- Building the discovery deck.

## Capabilities

### New Capabilities
- `bandcamp-embed`: finding an act's player ID, keeping it, the weekly run, and showing the player on event listings and (as a rule for the deck) elsewhere.

### Modified Capabilities
- `artist-records`: "Bandcamp only as a link" is replaced by a narrow permission to read a player ID, and records keep the player fields.
- `band-pages`: the artist and band pages show the Bandcamp player.
- `scheduled-jobs`: the weekly job runs the new command.

## Impact

- **Code:** `MusicAct` gains `bandcamp_embed_kind`, `bandcamp_embed_id`, `bandcamp_embed_status`, `bandcamp_embed_checked_at` and `bandcamp_embed_for`, with a migration; a new `core/bandcamp_embeds.py` and the command; `artist_previews` (including its early return when no other service is on), `event.html` and `core/js/artist_preview.js` (its click selector) gain a Bandcamp button; the band page template gains the player; `MusicActAdmin` gains a fieldset and re-renders affected events on save, clear, delete and review-mark changes, as do the performer-link rebuild and `mark_ready`/`import_act_list`; `core/act_export.py` decides on the new columns; `bin/weekly.sh`.
- **Extra requests:** besides the act's page, the command asks for its `/music` page when the front page has no music tile and for up to three players' pages, so up to five requests an act; this goes beyond the owner's "fetch the page once" and is an open question in the design.
- **Services:** bandcamp.com itself, free, no key, one page and up to three player checks per act, about two seconds apart. No paid API.
- **Rules changed:** the "never request anything from Bandcamp" rule in AGENTS.md (including the `read_artist_link_hubs` pipeline entry's "weekly, last" and "never Bandcamp" wording), PRODUCT.md, `core/artists.py` and the artist-records spec.
- **Ordering:** `add-artist-link-hub-links` also edits the Bandcamp-link requirement (artist-records) and the weekly-jobs requirement (scheduled-jobs, whose list here includes `read_artist_link_hubs`); archive it first. Its code is already in the repository, but its spec files are not yet in the main specs.
