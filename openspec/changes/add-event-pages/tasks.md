## 1. Before building

- [ ] 1.1 Archive `add-band-pages` (all its tasks are done), so the `band-pages` spec this change modifies exists; verify `openspec validate add-event-pages` no longer reports that archive would refuse the `band-pages` delta.
- [ ] 1.2 Take a database backup (`pg_dump -Fc` to `~/.local/share/nycnoise-backups/`) and create this change's worktree and database, per the worktree-per-change rule; verify the dev server runs from the worktree on its own port.

## 2. Reading the billing

- [ ] 2.1 Add `billing(event)` to `core/artist_names.py`, returning the title line, headliner and openers (design decision 2), and verify with unit tests for every `event-listing` scenario: headliner and openers, no act in the title ("Bluegrass Jam" with and without artists), a title that adds something ("Halloween Show"), a title that is only the names ("Dev Lemons, Venus & the Flytraps"), the headliner named in both ("Kim Deal" with "Kim Deal, Pile"), and the presenter prefix.
- [ ] 2.2 Add the fallback for titles the names cover poorly (design: Risks) and verify with tests built from the 2026-10-30 listings (Nekrogoblikon, Disko Lunatics, Under 21 Open Mic, Jeff "The Codfather" Acoustic Trio).

## 3. The listing

- [ ] 3.1 Rewrite `core/templates/core/event.html` to the title line, the headline linking to `/event/<id>`, the bold larger headliner and "with" openers, with no performer links and no "info" link, keeping the `data-` attributes, price, venue, description, access notes, tix badge, icon placeholder and play buttons; verify with listing tests for each `event-listing` requirement, including an event without performers.
- [ ] 3.2 Style the headline, headliner, openers and title line in `core/static/core/scss/core.scss` (headliner one step larger, openers regular, title line small and quiet) and verify `core/tests/test_scss.py` compiles and the homepage renders at 390px with no sideways scroll.
- [ ] 3.3 Remove `listing_parts`, `linked_parts` and performer-driven re-rendering (the `rebake` calls and the delete signals in `CoreConfig.ready`) now that rows don't depend on performers; verify the event-performer tests still pass with the listing assertions moved to the event page tests.
- [ ] 3.4 Verify the day map still places and labels events from the new rows (the map test, and a look at a day with three venues).

## 4. The event page

- [ ] 4.1 Turn `core/views/event_redirect.py` into the event page view at `/event/<id>`, named `event_page`: approved events only (404 otherwise), the share metadata kept, `noindex`; update the share icon, calendar feeds and band page to the new name, remove `core/empty.html` if nothing else uses it; verify with view tests for an approved, a past, an unapproved and an unknown event, and the share-preview title.
- [ ] 4.2 Move the band page's card styles into a `_card.scss` partial imported by `band.scss` and a new `event_page.scss`, and verify the band page tests and `test_scss.py` still pass with the band page unchanged on screen.
- [ ] 4.3 Build `core/templates/core/event_page.html`: the date and time tab, the title line, the headliner and openers with performers linked (including the occasion-prefix case), the lavender strip with the icon row, the venue, price, ages and access fields, the description, the play buttons, and the cancelled and past states; verify with tests for every `event-pages` scenario on what the page shows and the acts' links.
- [ ] 4.4 Add the "Tickets ↗" and "Venue's page ↗" links with normalized URL comparison (design decision 5), and verify tests for two different links, the same link (including a trailing slash and a `utm_` query), and only one link.
- [ ] 4.5 Check the page at 390px and 1440px, light and dark, and verify the phone scenario: the date, headliner and venue in the first screen, no sideways scroll, contrast passing the design check.

## 5. Finish

- [ ] 5.1 Update the `band-pages` tests for the modified "Events link to their acts" requirement (no listing links; links on the event page), and verify every scenario in this change's three spec files has a passing test.
- [ ] 5.2 Run the whole suite with the network blocked and verify it passes.
- [ ] 5.3 Run `resave_all_events` locally and check the homepage, a saved-shows page, a search and three event pages by eye.
- [ ] 5.4 Update `PRODUCTION.md` (the event page, and the `resave_all_events` run after deploy) and `DESIGN.md` (the listing's headline and the event card); verify both describe the shipped behavior.
