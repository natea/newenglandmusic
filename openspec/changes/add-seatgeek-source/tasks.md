## 1. Client and the coverage check

- [ ] 1.1 The user gets a SeatGeek client ID (waiting on SeatGeek's approval since 2026-10-26) and adds `SEATGEEK_CLIENT_ID` to `.env`; add it to `.env.example`. Verify: it's set (checked without printing it).
- [ ] 1.2 Add `core/event_fetching/seatgeek.py`, modelled on `ticketmaster.py`, with the client ID kept out of errors. Record fixtures once from the real API, with the client ID stripped. Verify: client tests that replay the fixtures with a fake session pass, with network blocked.
- [ ] 1.3 Move `find_match` into `core/venue_matching.py` as a shared function, keeping its behaviour. Verify: the existing `match_ticketmaster_venues` tests pass unchanged.
- [ ] 1.4 Add a SeatGeek check to `measure_api_coverage`. Verify: a test with a mocked client. Then run it for real, log it to `logs/`, and record the totals under Open Questions in design.md.
- [ ] 1.5 Show the coverage results to the user and record their decision in design.md. If they decline, drop this change.

## 2. Linking venues

- [ ] 2.1 Add `Venue.seatgeek_venue_id` and `Event.Source.SEATGEEK`, with their migration. Add the ID to the venue admin's "Event sources" section, its search, and a "linked to SeatGeek" filter. Verify: a test for "Admin sets the SeatGeek venue", and a sheet-sync test showing it's left unchanged.
- [ ] 2.2 Add `match_seatgeek_venues` (`--sheet-ids` / `--all` / `--recheck` / `--dry-run`), recorded as a job run. Verify: tests for "One clear match" and "Ambiguous".

## 3. Fetching events

- [ ] 3.1 In `fetch_events`, add SeatGeek after Eventbrite in the precedence, and fetch SeatGeek targets, keeping concerts only, with `seatgeek:` external IDs. Verify: tests for "Concerts only" and "Linked to Ticketmaster and SeatGeek".
- [ ] 3.2 Add `seatgeek failed:` to `PROBLEM_PREFIXES`, and handle a missing client ID with a note. Verify: a test for "API error" and for a missing client ID.

## 4. Docs and a real run

- [ ] 4.1 Update `PRODUCTION.md` (the key, the matching command, the terms check) and `AGENTS.md`. Verify by reading both.
- [ ] 4.2 Run the full suite with outbound network blocked, then link the venues covered in 1.4 and fetch them. Verify: every test passes and the job run shows SeatGeek events.
