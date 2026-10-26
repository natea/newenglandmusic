## 1. Client and the coverage check

- [x] 1.1 The user creates an Eventbrite private token and adds `EVENTBRITE_API_KEY` to `.env`. Verify: it's set, and `/v3/users/me/` accepts it (checked without printing it). (done 2026-10-26)
- [x] 1.2 Add `core/event_fetching/eventbrite.py`, modelled on `ticketmaster.py`, with a rate-limited client, event-to-dict conversion and the key kept out of errors. Record fixtures once from the real API, with the key and personal data stripped. Verify: client tests that replay the fixtures with a fake session pass, with network blocked.
- [x] 1.3 Add `measure_api_coverage`, a dry run that saves nothing. For each venue, it reports whether Eventbrite finds its organizer and how many upcoming events it lists. It covers the venues with ticketing-page failures in the latest fetch's job run, and every venue whose platforms include eventbrite, etix or axs. Verify: a test with mocked clients. Then run it for real, log it to `logs/`, and record the totals under Open Questions in design.md.
- [x] 1.4 Show the coverage results to the user, and record their decision. Verify: the decision is written in design.md, SeatGeek is split into `add-seatgeek-source`, and `openspec validate` passes for both changes. (2026-10-26: build Eventbrite now)

## 2. Linking venues

- [x] 2.1 Add `Venue.eventbrite_organizer_id` and `Event.Source.EVENTBRITE`, with their migration. Add the organizer ID to the venue admin's "Event sources" section, its search, and a "linked to Eventbrite" filter. Verify: a test for "Admin sets the organizer", and a sheet-sync test showing it's left unchanged.
- [x] 2.2 Add `match_eventbrite_organizers` (`--sheet-ids` / `--all` / `--recheck` / `--dry-run`), recorded as a job run, with polite page fetching shared with `measure_api_coverage`. Verify: tests for "One organizer", "Several organizers", "Organizer page linked" and "Organizer's events are all elsewhere", with venue-page HTML and a mocked client.

## 3. Fetching events

- [x] 3.1 In `fetch_events`, apply the precedence (Ticketmaster, then Eventbrite, but never over iCal or JSON-LD), and fetch Eventbrite targets, keeping only events at the venue, with `eventbrite:` external IDs and the `eventbrite` source. Note how many upcoming unapproved events from the venue's earlier ticketing or AI source remain, for an admin to tidy. Verify: tests for "Organizer with events elsewhere", "Re-fetch updates instead of duplicating" and "Linked to Ticketmaster and Eventbrite".
- [x] 3.2 Add `eventbrite failed:` to `PROBLEM_PREFIXES`, and handle a missing key with a note. Verify: tests for "API error" and "No token".

## 4. Docs and a real run

- [x] 4.1 Update `PRODUCTION.md` (the key, the matching command in the job table, and the terms check on the launch checklist) and `AGENTS.md` (the pipeline and the rate limit). Verify by reading both.
- [ ] 4.2 Run the full suite with outbound network blocked. Then link the venues covered in 1.3 and run `fetch_events --sheet-ids` for them. Verify: every test passes, the job run shows Eventbrite events, and those venues' fetch statuses no longer show their old ticketing-page failures.

## Workflow follow-up

- Archive with `/opsx:archive add-eventbrite-source` once every task is checked. Then update `event-import`'s "Venues are fetched according to the report" to name the Eventbrite source.
