## 1. Clients and the coverage check

- [ ] 1.1 The user creates an Eventbrite private token and a SeatGeek client ID, and adds `EVENTBRITE_TOKEN` and `SEATGEEK_CLIENT_ID` to `.env`. Add both to `.env.example`. Verify: both are set (checked without printing them).
- [ ] 1.2 Add `core/event_fetching/eventbrite.py` and `core/event_fetching/seatgeek.py`, modelled on `ticketmaster.py`. Include rate-limited clients, event-to-dict conversion, and keys kept out of errors. Record fixtures once from the real APIs, with keys and personal data stripped. Verify: client tests that replay the fixtures with a fake session pass, with network blocked.
- [ ] 1.3 Add `measure_api_coverage`, a dry run that saves nothing. For each venue, it reports whether each API finds it and how many upcoming events it lists. It covers the venues with ticketing-page failures in the latest fetch's job run, and every venue whose platforms include eventbrite, etix or axs. Verify: a test with mocked clients. Then run it for real, log it to `logs/`, and record the totals under Open Questions in design.md.
- [ ] 1.4 Show the coverage results to the user, and record their decision on which APIs to build. Drop the tasks and spec of any API they decline. Verify: the decision is written in design.md, and `openspec validate add-eventbrite-seatgeek-sources` passes.

## 2. Linking venues

- [ ] 2.1 Add `Venue.eventbrite_organizer_id` and `Venue.seatgeek_venue_id`, with their migration. Add them to the venue admin's "Event sources" section, its search, and "linked to Eventbrite" / "linked to SeatGeek" filters. Verify: tests for "Admin sets the organizer" and "Admin sets the SeatGeek venue", and a sheet-sync test showing both are left unchanged.
- [ ] 2.2 Move `find_match` into `core/venue_matching.py` as a shared function, keeping its behaviour. Verify: the existing `match_ticketmaster_venues` tests pass unchanged.
- [ ] 2.3 Add `match_eventbrite_organizers` (`--sheet-ids` / `--all` / `--recheck` / `--dry-run`), recorded as a job run, with polite page fetching. Verify: tests for "One organizer" and "Several organizers", with venue-page HTML fixtures and a mocked client.
- [ ] 2.4 Add `match_seatgeek_venues` (the same options), recorded as a job run. Verify: tests for "One clear match" and "Ambiguous".

## 3. Fetching events

- [ ] 3.1 In `fetch_events`, apply the precedence (Ticketmaster, then Eventbrite, then SeatGeek, but never over iCal or JSON-LD), and fetch Eventbrite and SeatGeek targets. Keep only events at the venue (Eventbrite) and concerts (SeatGeek), with `eventbrite:` / `seatgeek:` external IDs. Report the old source's unapproved events left behind. Verify: tests for "Organizer with events elsewhere", "Re-fetch updates instead of duplicating", "Concerts only" and "Linked to Ticketmaster and SeatGeek".
- [ ] 3.2 Add `eventbrite failed:` and `seatgeek failed:` to `PROBLEM_PREFIXES`, and handle missing keys with a note. Verify: tests for both "API error" scenarios, and for a missing key.

## 4. Docs and a real run

- [ ] 4.1 Update `PRODUCTION.md` (the keys, the two matching commands in the job table, and the terms check on the launch checklist) and `AGENTS.md` (the pipeline and the rate limits). Verify by reading both.
- [ ] 4.2 Run the full suite with outbound network blocked. Then link the venues covered in 1.3 and run `fetch_events --sheet-ids` for them. Verify: every test passes, the job run shows the new sources' events, and those venues' fetch statuses no longer show their old ticketing-page failures.

## Workflow follow-up

- Archive with `/opsx:archive add-eventbrite-seatgeek-sources` once every task is checked, after `store-event-sources-in-db` is archived. Then update `event-import`'s "Venues are fetched according to the report" to name the new API sources.
