# Tasks

## 1. Model and configuration

- [x] 1.1 Add `Venue.ticketmaster_venue_id` (CharField, null/blank, db_index) and the `ticketmaster` choice on `Event.source`; run `makemigrations` and `migrate` and verify the migration applies and reverses cleanly
- [x] 1.2 Show `ticketmaster_venue_id` in `VenueAdmin` (field, search, and a "linked to Ticketmaster" filter); verify by setting and clearing an ID on a venue at http://localhost:8001/admin/core/venue/
- [x] 1.3 Add a test that `sync_venues_from_gsheets` leaves `ticketmaster_venue_id` unchanged when re-syncing a venue, and verify it passes
- [x] 1.4 Add `TICKETMASTER_API_KEY=` to `.env.example` with a comment linking to developer.ticketmaster.com; verify `.env` remains git-ignored

## 2. Discovery API client and event mapping

- [x] 2.1 Create `core/event_fetching/ticketmaster.py` with a throttled client (≥0.25s between calls, 2 retries with back-off on 429/5xx, key never included in logged URLs or errors); verify with unit tests using mocked responses for success, 429-then-success and repeated 5xx
- [x] 2.2 Implement `venue_events(venue_id)` (upcoming, `sort=date,asc`, `size=50`, `source=ticketmaster,universe,frontgate`) and `to_event_dict(event)` per design decision 5; verify with tests on recorded JSON fixtures covering headliner + support, TBA time, cancelled, rescheduled, a non-Music segment (skipped) and missing price
- [x] 2.3 Implement `search_venues(name, state_code)` returning id, name, address, city and coordinates; verify with a fixture-based test
- [x] 2.4 With a real key, fetch events for one known venue (e.g. Paradise Rock Club), save the raw response under `core/tests/fixtures/ticketmaster/`, and confirm that excluding `tmr` doesn't drop primary listings; record the finding in design.md if it changes decision 6

## 3. Venue matching command

- [x] 3.1 Add `match_ticketmaster_venues` with `--sheet-ids`, `--all`, `--recheck` and `--dry-run`; by default select active venues whose report `platforms` includes ticketmaster; error clearly without `TICKETMASTER_API_KEY`; verify with a test for the missing-key error
- [x] 3.2 Implement name normalization, haversine distance and the unique-match-within-1 km rule, with a city-name fallback search; verify with unit tests for exact match, containment ("MGM Music Hall" vs "MGM Music Hall at Fenway"), two candidates (ambiguous), a distant name match and no candidates
- [x] 3.3 (Unblocked by `add-venue-place-lookup`. Against the exact locations, the dry run links 8 of 23; the other 15 fail on the loose name rule or on duplicate Ticketmaster listings. The name rule needs a decision before this task can be done.) Print a report grouped as linked / already linked / ambiguous (with candidate id, name, address, distance) / unmatched; verify a `--dry-run` over the 23 Ticketmaster-listing venues saves nothing and lists each venue once
- [x] 3.4 Document the command's usage in its module docstring, matching the style of `fetch_events`

## 4. fetch_events integration

- [x] 4.1 Route linked venues to the Ticketmaster source per design decision 4 (keep ical/json-ld; replace ticketing/ai; include linked venues without a usable report row) and add `--skip-ticketmaster`; verify with tests on `select_targets` for each case
- [x] 4.2 Fetch Ticketmaster events before the Scrapy crawl, feed them into the existing `events_by_venue`/notes reporting and `save_event` path, and skip with a note when the key is missing; verify with a test that mocks the client and checks events are saved unapproved with source `ticketmaster` and external_id `tm:<id>`, that re-import keeps approval, and that `--dry-run` saves nothing
- [x] 4.3 Update the `fetch_events` docstring to list the ticketmaster source and `TICKETMASTER_API_KEY`; verify `python manage.py fetch_events --help` shows `--skip-ticketmaster`

## 5. End-to-end check

- [x] 5.1 Run `match_ticketmaster_venues --dry-run`, then for real; settle ambiguous venues in the admin; verify the number of linked venues
  - Real run (2026-10-25), with the exact-name rule: 14 venues linked.
  - 5 more set by hand where only one duplicate listing has upcoming events: House of Blues, Brighton Music Hall, The Fillmore, The Stone Pony, Funk 'n Waffles. That makes 19 of 23.
  - Left unlinked: Merriweather (wrong town in the sheet), Club Passim and The State Theater (no listing), and Empire Live / Empire Underground (one sheet row, two Ticketmaster rooms).
- [x] 5.2 Run `fetch_events --sheet-ids <linked ids> --dry-run`, then for real; verify upcoming events now exist for previously empty venues (e.g. Paradise Rock Club, MGM Music Hall, 9:30 Club) and that no venue has duplicate events from two sources
  - Real run: 458 created, 123 updated (log: `logs/fetch_ticketmaster-2026-10-25.log`). Every linked venue has upcoming events, e.g. Paradise 50, MGM 46, 9:30 Club 46, Brighton 50, Mr. Smalls 23.
  - The dry run exposed the TicketWeb gap in design decision 6, now fixed.
  - No duplicates across sources. Aura's one leftover `ticketing` event is an Eventbrite show that isn't on Ticketmaster.
- [x] 5.3 Run the full test suite and verify it passes Done: 255 tests pass with outbound network blocked.

## 6. Ticketmaster replaces iCal (decided after the first real run)

- [x] 6.1 Route linked iCal venues to Ticketmaster in `select_targets` (keep json-ld); update the routing tests so the ical venue goes to ticketmaster, and verify that they pass
- [x] 6.2 After a successful API fetch, delete the venue's upcoming unapproved `ical` events (not on a dry run or a failed request) and report how many; test deletion, and that approved, past and other-source events are kept, on a dry run and on API failure. Verify that the tests pass
- [x] 6.3 Run `fetch_events --sheet-ids V0078,V0272`, logging to `logs/`, and record the event counts for The Anthem and Blue Ocean; run the full suite with outbound network blocked
  - Result (log: `logs/fetch_events-2026-10-25.log`): The Anthem went from 1 event to 35 from Ticketmaster; Blue Ocean from 3 to 31, and its 3 unapproved iCal events were removed.
  - The Anthem's one iCal event (Tinashe, 2027-04-26) was approved earlier, so it was kept. Ticketmaster has the same show (event 2246, unapproved). Only one copy is on the site; an admin can delete the Ticketmaster copy.
  - Full suite: 257 tests pass with outbound network blocked.

## Workflow follow-up

- Review the Ticketmaster Partner API Terms (attribution, data retention) before any public deployment.
- Archive the change with `openspec archive add-ticketmaster-discovery-api` after implementation is reviewed.
