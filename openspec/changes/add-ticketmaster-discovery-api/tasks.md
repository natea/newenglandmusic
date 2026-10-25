# Tasks

## 1. Model and configuration

- [ ] 1.1 Add `Venue.ticketmaster_venue_id` (CharField, null/blank, db_index) and the `ticketmaster` choice on `Event.source`; run `makemigrations` and `migrate` and verify the migration applies and reverses cleanly
- [ ] 1.2 Show `ticketmaster_venue_id` in `VenueAdmin` (field, search, and a "linked to Ticketmaster" filter); verify by setting and clearing an ID on a venue at http://localhost:8001/admin/core/venue/
- [ ] 1.3 Add a test that `sync_venues_from_gsheets` leaves `ticketmaster_venue_id` unchanged when re-syncing a venue, and verify it passes
- [ ] 1.4 Add `TICKETMASTER_API_KEY=` to `.env.example` with a comment linking to developer.ticketmaster.com; verify `.env` remains git-ignored

## 2. Discovery API client and event mapping

- [ ] 2.1 Create `core/event_fetching/ticketmaster.py` with a throttled client (≥0.25s between calls, 2 retries with back-off on 429/5xx, key never included in logged URLs or errors); verify with unit tests using mocked responses for success, 429-then-success and repeated 5xx
- [ ] 2.2 Implement `venue_events(venue_id)` (upcoming, `sort=date,asc`, `size=50`, `source=ticketmaster,universe,frontgate`) and `to_event_dict(event)` per design decision 5; verify with tests on recorded JSON fixtures covering headliner + support, TBA time, cancelled, rescheduled, a non-Music segment (skipped) and missing price
- [ ] 2.3 Implement `search_venues(name, state_code)` returning id, name, address, city and coordinates; verify with a fixture-based test
- [ ] 2.4 With a real key, fetch events for one known venue (e.g. Paradise Rock Club), save the raw response under `core/tests/fixtures/ticketmaster/`, and confirm that excluding `tmr` doesn't drop primary listings; record the finding in design.md if it changes decision 6

## 3. Venue matching command

- [ ] 3.1 Add `match_ticketmaster_venues` with `--sheet-ids`, `--all`, `--recheck` and `--dry-run`; by default select active venues whose report `platforms` includes ticketmaster; error clearly without `TICKETMASTER_API_KEY`; verify with a test for the missing-key error
- [ ] 3.2 Implement name normalization, haversine distance and the unique-match-within-1 km rule, with a city-name fallback search; verify with unit tests for exact match, containment ("MGM Music Hall" vs "MGM Music Hall at Fenway"), two candidates (ambiguous), a distant name match and no candidates
- [ ] 3.3 Print a report grouped as linked / already linked / ambiguous (with candidate id, name, address, distance) / unmatched; verify a `--dry-run` over the 23 Ticketmaster-listing venues saves nothing and lists each venue once
- [ ] 3.4 Document the command's usage in its module docstring, matching the style of `fetch_events`

## 4. fetch_events integration

- [ ] 4.1 Route linked venues to the Ticketmaster source per design decision 4 (keep ical/json-ld; replace ticketing/ai; include linked venues without a usable report row) and add `--skip-ticketmaster`; verify with tests on `select_targets` for each case
- [ ] 4.2 Fetch Ticketmaster events before the Scrapy crawl, feed them into the existing `events_by_venue`/notes reporting and `save_event` path, and skip with a note when the key is missing; verify with a test that mocks the client and checks events are saved unapproved with source `ticketmaster` and external_id `tm:<id>`, that re-import keeps approval, and that `--dry-run` saves nothing
- [ ] 4.3 Update the `fetch_events` docstring to list the ticketmaster source and `TICKETMASTER_API_KEY`; verify `python manage.py fetch_events --help` shows `--skip-ticketmaster`

## 5. End-to-end check

- [ ] 5.1 Run `match_ticketmaster_venues --dry-run`, then for real; settle ambiguous venues in the admin; verify the number of linked venues
- [ ] 5.2 Run `fetch_events --sheet-ids <linked ids> --dry-run`, then for real; verify upcoming events now exist for previously empty venues (e.g. Paradise Rock Club, MGM Music Hall, 9:30 Club) and that no venue has duplicate events from two sources
- [ ] 5.3 Run the full test suite and verify it passes

## Workflow follow-up

- Review the Ticketmaster Partner API Terms (attribution, data retention) before any public deployment.
- Archive the change with `openspec archive add-ticketmaster-discovery-api` after implementation is reviewed.
