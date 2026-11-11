Issue: [#47 Embedded Bandcamp player on event listings, artist and band pages, and the discovery deck](https://github.com/natea/newenglandmusic/issues/47)

Issue: [#47 Embedded Bandcamp player on event listings, artist and band pages, and the discovery deck](https://github.com/natea/newenglandmusic/issues/47)

## 1. Research and data

- [ ] 1.1 Fetch a fresh sample of about 25 acts' Bandcamp pages (read-only, robots.txt obeyed, two seconds apart) and confirm the shapes in the design: the JSON-LD `albumRelease` `item_id`, a track's page properties, grid tile markup and merch tiles' prefix, the `/music` path, and the player page's "not available" marker. Save sanitised pages in `core/tests/fixtures/bandcamp/` and update the design if they differ.
- [ ] 1.2 Add `bandcamp_embed_kind`, `bandcamp_embed_id` (digits only), `bandcamp_embed_status`, `bandcamp_embed_checked_at` and `bandcamp_embed_for` to `MusicAct`, with a migration and the player-address helper. Write the automated tests for "Player address from an album ID", "The URL a player was read from", "Stale player is not usable" and "An ID that is not a number", and check `makemigrations --check` is clean.

## 2. The lookup

- [ ] 2.1 Write `core/bandcamp_embeds.py`: candidates from a release page (JSON-LD, page properties) and from a grid, merch skipped, `/music` fallback, the player-availability check with at most three tries. Write the automated tests for "Redirect to a featured album", "Redirect to a track", "Discography grid", "Merchandise first", "Physical-only first release" and "Nothing playable".
- [ ] 2.2 Write `find_bandcamp_embeds` as a `RecordedCommand` (`--limit`, `--refresh`, `--dry-run`), with robots.txt, the user agent, two-second pacing, redirects refused off Bandcamp, statuses, the three-blocks stop, `due()`, `queryset.update()` writes, re-rendering changed acts' events, and `job_summary` and `job_problems`. Write the automated tests, with a fake session, for "Robots forbids it", "A deleted page", "A redirect off Bandcamp", "A failed refresh of a found player", "Blocked repeatedly", "Nothing else is kept", "Never looked up", "Recently looked up", "Old no-playable result", "Address changed", "A failed refresh keeps the ID", "Dry run", "Limit", "Default cap", "Refresh", "An editor's player stays" and "A page view", asserting request counts.
- [ ] 2.3 Add the step to `bin/weekly.sh`, update the `WEEKLY` list in `core/tests/test_scheduled_jobs.py`, and write the automated tests for "Weekly run" and "Bandcamp step fails".

## 3. Admin and records

- [ ] 3.1 Add the "Bandcamp player" fieldset, validation, "editor" marking, clearing, and the status filter to `MusicActAdmin`; keep the import, enrichment and `clear_musicbrainz` away from the fields. Re-render the affected events on every admin save, clear and delete, on the review-mark toggles and the act-list import, and when `EventPerformer` rows are rebuilt, through one shared helper. Write the automated tests for "Editor sets an ID", "An editor's player is shown", "Events re-rendered after an editor's change", "Events re-rendered after performer links change", "Clearing", "Filter", "Clearing a match", "Import leaves the player" and "The import asks Bandcamp for nothing", for an artist and a band.
- [ ] 3.2 Add the fields to `core/act_export.py` as decided in the design (or to `NOT_EXPORTED`) and keep `test_act_export` passing (the export code is already in the repository).

## 4. Showing the player

- [ ] 4.1 Add the `bandcamp` key to `event_artist_previews` (performers matched by name, held-for-review and stale-address acts excluded), drop the early return that needs another service on, give `event.html`'s `{% if artist_previews %}` and the click selector in `core/js/artist_preview.js` a Bandcamp entry and add the click handler, and show only usable players, plus the screen-order function for the deck. Write the automated tests for "Event row with a player", "Only Bandcamp", "No other service configured" (all three previews off), "Nothing loads until pressed", "Act with no usable player", "Events re-rendered", "Deck order", "Full order" and "Only Bandcamp in the deck", and the browser test (Playwright, Bandcamp intercepted, other outbound network blocked) for "Pressing the event button" and "Event button without JavaScript".
- [ ] 4.2 Add the "Listen on Bandcamp" section to the band template and `act_page.py`. Write the automated tests for "Band page with a player", "Pressing play on a band page" (browser), "Band page with no player" and "Band page without JavaScript" in the band-pages spec.
- [ ] 4.3 Check the site's content-security policy and privacy page for Bandcamp frames and cookies, and update them as decided.

## 5. The rule and the finish

- [ ] 5.1 Reword the Bandcamp rule in `core/artists.py`, AGENTS.md (including the `read_artist_link_hubs` pipeline entry's "weekly, last" and "never Bandcamp") and PRODUCT.md as the design says, and document the command and its pacing in PRODUCTION.md (with the `bin/weekly.sh` header comment and PRODUCTION.md's weekly job description) and AGENTS.md's pipeline section.
- [ ] 5.2 Run the suite with outbound network blocked, then a real `find_bandcamp_embeds --limit 25 --dry-run` and a real run, logged to `logs/find_bandcamp_embeds-YYYY-MM-DD.log`. Update the design if the live pages contradict it, and verify that every scenario has a passing test.
