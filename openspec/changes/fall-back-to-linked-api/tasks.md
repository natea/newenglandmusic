## 1. Fallback in fetch_events

- [ ] 1.1 After the crawl, find the iCal and JSON-LD targets that got no events and at least one error, and pick each one's fallback API (Ticketmaster, then Eventbrite), honouring `--skip-ticketmaster` and `--skip-eventbrite`. Verify: tests for "Saved source works", "Not linked" and "API skipped".
- [ ] 1.2 Fetch those targets from their API with the existing `fetch_from_ticketmaster` / `fetch_from_eventbrite`, switch their source to the API, drop their queued AI pages, and leave their iCal events in place. Verify: tests for "JSON-LD blocked, linked to Eventbrite" and "Unparseable iCal feed, linked to Eventbrite", and a test that a Ticketmaster fallback removes no iCal events.
- [ ] 1.3 Reword the crawl's failure notes when the fallback gets events, so they aren't problems; keep them, plus the API's failure, when it doesn't. Verify: tests for "Fallback works" and "Fallback fails too", checking the job run's problems and the venue's fetch status.

## 2. Docs and a real run

- [ ] 2.1 Update `fetch_events`'s module docstring and the AGENTS.md pipeline note. Verify by reading both.
- [ ] 2.2 Run the full suite with outbound network blocked. After release, refetch The Main Pub (V0026) on Render. Verify: every test passes, and the venue gets its events from Eventbrite with no problems listed.
