Issue: [#26 build a tinder-style band discovery tool on the site](https://github.com/natea/newenglandmusic/issues/26)

## 1. Deck and card

- [ ] 1.1 Add `/discover` and a view that builds the deck: live acts with at least one approved upcoming show, found through their performances, ignoring the remembered area filter and not changing it, in a random order per visit (seedable in tests, with no cache headers), built in bulk rather than a query per act, leaving out cancelled shows (`is_cancelled=False`) and using the same start-of-today bound as `upcoming_shows` so the deck and band page agree, reading events through the approved-only `Event.objects` rather than the default related manager, with the empty state and a link to the listings. Verify with view tests for the deck, acts left out (past only, held for review, cancelled only, an unapproved upcoming show only), the cancelled-shows scenario, one card for several shows, the empty page and the area filter scenarios.
- [ ] 1.2 Build an act-level entry point for the play buttons beside the event one, reusing the listing's candidate-key and button functions and the same stored links and switches, matching the act's own name exactly (no duo or occasion fallbacks). Verify with tests for the Spotify-only, none and every-service cases, and that the page makes no outside request, plus a browser test that no request goes to Spotify, Apple Music or YouTube before a play button is clicked.
- [ ] 1.3 Build the card template: name, kind, town, photo with credit, next show, play buttons, link to the act's page. Verify with tests for the card contents, no-match and no-photo scenarios.

## 2. Swiping and the picker

- [ ] 2.1 Write the script for swipe, buttons and arrow keys, passing without storing anything, and the end-of-deck state. Verify with browser tests for pass by swipe, button and key, and the end of the deck.
- [ ] 2.2 Build the show picker: the act's shows soonest first, ticked only if already saved, confirm as a change (add newly ticked, remove unticked), close, and unchanged-ticks behavior. Verify with browser tests for the picker's list, closing, nothing ticked, ticks unchanged with a saved show, removing the last saved show, keeping on the last card, and the already-saved scenario.
- [ ] 2.3 Expose a small API from `saved_shows.js` of the shape `window.SavedShows.apply(add, remove)` that applies a change to the current cookie (never replacing it) and re-renders the header count and save buttons, and use it to write the picker's result in one write. Verify with browser tests for saving two shows, other saved shows surviving a confirm, the header count, `/saved` listing them, the 300-show limit, and removal by unticking, and re-run the existing saved-shows browser tests, since that script loads on every page.

## 3. Access and links

- [ ] 3.1 Give the deck keyboard access, named controls, a live announcement of the current act, swipes that ignore pointer events starting inside the open player, card markup using the `.artist-previews` class and data attributes the player script expects, a focus-managed picker and reduced-motion handling. Verify with browser tests for keyboard-only use and the announcement.
- [ ] 3.2 Make the page work without JavaScript: stacked cards, each with its shows and the existing save bookmark. Verify with a test that the page lists every card with bookmarks that post to `/saved/toggle/<id>` (with `next=/discover` and a per-show anchor, unique across all cards) and return to the page.
- [ ] 3.3 Add the "Discover bands" menu link as an idempotent, reversible data migration creating a header and footer `MenuItem`, like `0102_bands_menu_item.py`. Verify with tests for the menu link and that running the migration twice creates one row.

## 4. Finish

- [ ] 4.1 Check the deck at phone and desktop widths, with an act that has many shows, one with no photo, and one with all three play buttons; run the design review against the chosen sketch.
- [ ] 4.2 Run the whole suite with the network blocked and verify it passes, with every scenario in `specs/band-discovery/spec.md` covered by a test.
- [ ] 4.3 Update `PRODUCTION.md` with a deploy note that the migration adds the menu item, update the stale "nothing visitors see reads these yet" docstring on `EventPerformer`, and note the page in the docs that list the site's pages.
