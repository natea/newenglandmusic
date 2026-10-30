## 1. Before building

- [ ] 1.1 Confirm `add-event-pages` is built (its `billing()`, `_card.scss` and event page exist); if not, add those first as described in its design, and verify their tests pass.
- [ ] 1.2 Back up the database and create this change's worktree and database; verify the dev server runs from the worktree.

## 2. Slugs

- [ ] 2.1 Add `Venue.slug` with a migration that fills it for every venue (town added on a clash), fill it in `save()` for new venues, and keep it out of the sheet sync; verify with tests for a new venue, two venues with one name, and a sheet sync that renames a venue without changing its slug.

## 3. The page

- [ ] 3.1 Add `core/views/venue_page.py` at `/venues/<slug>`: 404 for inactive or unknown venues, the upcoming approved shows in order, `noindex`, title and description; verify with view tests for an active, an inactive, an unknown and an unknown-status venue.
- [ ] 3.2 Build `core/templates/core/venue.html` and `venue.scss` to the chosen composition (`.impeccable/mocks/decision/poster-column.html`): tab, fact line with the Map and Open booking links, "The bill" with nights linking to event pages and today's nights marked, the empty state, then "Playing here" and "Getting here"; verify with tests for every `venue-pages` scenario on the bill, the fact line, the sections and the map link.
- [ ] 3.3 Link the event page's venue name to the venue page and give `VenueAdmin` "View on site"; verify with tests for both links.

## 4. Finish

- [ ] 4.1 Check the page at 390px and 1440px with O'Brien's, a venue with no shows and a sparse venue, and verify the phone scenario and the design check; then run the Impeccable finish review against the direction contract and act on its verdict.
- [ ] 4.2 Run the whole suite with the network blocked and verify it passes, with every scenario in `specs/venue-pages/spec.md` covered.
- [ ] 4.3 Update `PRODUCTION.md` (venue pages and their slugs) and `DESIGN.md` (the venue page's bill), and verify both describe the shipped behavior.
