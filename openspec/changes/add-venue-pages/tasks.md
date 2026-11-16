## 1. Before building

- [x] 1.1 Confirm `add-event-pages` is built (its `billing()`, `_card.scss` and event page exist); if not, add those first as described in its design, and verify their tests pass. (Done: built on `add-event-pages`, PR #139.)
- [x] 1.2 Back up the database and create this change's worktree and database; verify the dev server runs from the worktree. (Done: this morning's production backup restored into `nycnoise_venue_pages_site`, served from the worktree on port 8006; all 729 venues got slugs.)

## 2. Slugs

- [x] 2.1 Add `Venue.slug` with a migration that fills it for every venue (town added on a clash), fill it in `save()` for new venues without ever rewriting an existing one, make it an editable, unique field in the venue admin, and keep it out of the manual sheet import; verify with tests for a new venue (including one added in the admin), two venues with one name, a rename in the admin keeping the slug, and a sheet import that renames a venue without changing its slug.

## 3. The page

- [x] 3.1 Add `core/views/venue_page.py` at `/venues/<slug>`: 404 for inactive, unknown and non-New England venues, the upcoming approved shows in order, a canonical link and no `noindex`, title and description; verify with view tests for an active, an inactive, an unknown, an unknown-status and a New York venue, and the indexing scenario.
- [x] 3.2 Build `core/templates/core/venue.html` and `venue.scss` to the chosen composition (`.impeccable/mocks/decision/poster-column.html`): tab, fact line with the sub-region (Massachusetts venues, linking to its listing), Map and Open booking links, "The bill" with nights linking to event pages and today's nights marked, the empty state, then "Playing here" and "Getting here"; verify with tests for every `venue-pages` scenario on the bill, the fact line, the sections and the map link.
- [x] 3.3 Link the event page's venue name to the venue page and give `VenueAdmin` "View on site"; verify with tests for both links.

## 4. Finish

- [x] 4.1 Check the page at 390px and 1440px with O'Brien's, a venue with no shows and a sparse venue, and verify the phone scenario and the design check; then run the Impeccable finish review against the direction contract and act on its verdict. (Done: O'Brien's at 390px and 1440px, Club Metronome with no shows at 390px; nothing scrolls sideways, and the name, fact line and first night are in the first screen. Fixed by eye: a doubled plum rule above the bill and above each section. Checked against the direction contract by hand rather than with the Impeccable finish-review agent.)
- [x] 4.2 Run the whole suite with the network blocked and verify it passes, with every scenario in `specs/venue-pages/spec.md` covered.
- [x] 4.3 Update `PRODUCTION.md` (venue pages and their slugs) and `DESIGN.md` (the venue page's bill), and verify both describe the shipped behavior.
