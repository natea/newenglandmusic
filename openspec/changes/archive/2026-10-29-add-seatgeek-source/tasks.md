## 1. Client and the coverage check

- [x] 1.1 The user gets a SeatGeek client ID and adds `SEATGEEK_CLIENT_ID` to `.env` (done 2026-10-29, with the secret; one test request returned 200); add it to `.env.example`. Verify: it's set (checked without printing it).
- [x] 1.2 Add `core/event_fetching/seatgeek.py`, modelled on `ticketmaster.py`, sending the client ID by HTTP Basic Auth, never in a URL. Record fixtures once from the real API, with the client ID stripped. Verify: client tests that replay the fixtures with a fake session pass, with network blocked.
- [x] 1.3 Move `find_match` into `core/venue_matching.py` as a shared function, keeping its behaviour. Verify: the existing `match_ticketmaster_venues` tests pass unchanged.
- [x] 1.4 Add a SeatGeek check to `measure_api_coverage`. Verify: a test with a mocked client. Then run it for real, log it to `logs/`, and record the totals under Open Questions in design.md.
- [x] 1.5 Show the coverage results to the user and record their decision in design.md. If they decline, drop this change.

## 2. Linking venues

- [x] 2.1 Add `Venue.seatgeek_venue_id`, `Venue.ticket_page_url` and `Event.Source.SEATGEEK`, with their migration. Add both fields to the venue admin's "Event sources" section, the ID to its search, and a "linked to SeatGeek" filter. Verify: a test for "Admin sets the SeatGeek venue", and a sheet-sync test showing both fields are left unchanged.
- [x] 2.2 Decide between a search per venue and the bulk venues file (Open Questions in design.md), then add `match_seatgeek_venues` (`--sheet-ids` / `--all` / `--recheck` / `--dry-run`), recorded as a job run. Verify: tests for "One clear match" and "Ambiguous".

## 3. Fetching events

- [x] 3.1 In `fetch_events`, add SeatGeek after Eventbrite in the precedence, and fetch SeatGeek targets, keeping concerts only, with `seatgeek:` external IDs. Verify: tests for "Concerts only" and "Linked to Ticketmaster and SeatGeek".
- [x] 3.2 Link SeatGeek events to the venue's ticket page (or else its website), and store the SeatGeek page only as the source URL. Verify: tests for "Venue sells through Etix", "No ticket page" and "SeatGeek link not shown".
- [x] 3.3 Add `seatgeek failed:` to `PROBLEM_PREFIXES`, and handle a missing client ID with a note. Verify: a test for "API error" and for a missing client ID.

## 4. Docs and a real run

- [x] 4.1 Update `PRODUCTION.md` (the key, the matching command, the terms check) and `AGENTS.md` (SeatGeek in the pipeline and the API limits, and that its links aren't shown). Verify by reading both.
- [x] 4.2 Run the full suite with outbound network blocked, then link the venues covered in 1.4, ask the user to fill in their ticket pages (or list them for the user), and fetch them. Verify: every test passes and the job run shows SeatGeek events.

## 5. Links to the show's own page (added 2026-10-29)

- [x] 5.1 Show each event's source, source page and external ID in the event admin, read-only, and add a "by source" filter. Verify: tests for the event page and the filter.
- [x] 5.2 Add `core/event_fetching/ticket_links.py`: find Etix and AXS show and venue links in a page's HTML, and match an event to the one show link whose slug starts with its title or headliner. Record trimmed venue HTML (Toad's Place, The Sinclair) in `core/tests/fixtures/ticket_links/`. Verify: tests for "Show's own page found" and "Recurring title" on the fixtures.
- [x] 5.3 In `fetch_from_seatgeek`, read each venue's events page once (robots.txt, the honest user agent, a timeout), link events to their show's page, and fill a blank ticket page from a single venue link with `queryset.update()`. Verify: tests for "Venue's list found on its site", "Ticket page already set" and "Venue's site can't be read", and that no request goes to etix.com or axs.com.
- [x] 5.4 In `fetch_events`, for SeatGeek-linked venues whose source is JSON-LD, fetch their SeatGeek concerts after the crawl and keep whichever source has more upcoming events, noting both counts. Verify: tests for "JSON-LD from a single show's page" and "JSON-LD lists more".
- [x] 5.5 Update `PRODUCTION.md` and `AGENTS.md` for the links, run the full suite with outbound network blocked, then refetch the 24 SeatGeek venues in the worktree database with `--skip-ai`. Verify: every test passes, and the run reports how many events got a show's own page.
