## Context

- **The Ticketmaster pattern this follows:**
  - `core/event_fetching/ticketmaster.py` has a rate-limited `TicketmasterClient` and `to_event_dict`.
  - `match_ticketmaster_venues` links venues using `core/venue_matching.py` (`names_match`, `distance_km`, `spelling_variants`), preferring listings with events.
  - `fetch_events.select_targets` swaps a linked venue's source to `ticketmaster`, unless its source is JSON-LD.
  - `fetch_ticketmaster` fetches linked venues, and records failures as `ticketmaster failed:` notes.
- **Problem notes:** `is_problem` recognises failures by note prefix (`PROBLEM_PREFIXES`), so the job run and the venue's fetch status pick them up.
- **Platform counts from the saved source checks:**
  - eventbrite: 61 venues, 57 not on Ticketmaster
  - etix: 21
  - dice: 10
  - tixr: 9
  - axs: 4
  - the rest are smaller
- **What the API offers:** a private token, from the account's API Keys page, is sent as a bearer token. The public event search is retired, so events are reached through known IDs: an event's details give its `organizer_id`, and an organizer's events can be listed.
- **SeatGeek** was part of this change until it was split out into `add-seatgeek-source` (2026-10-26), because its client ID is still waiting on SeatGeek's approval. That change adds SeatGeek after Eventbrite in the precedence below.

**Checked against the real Eventbrite API (2026-10-26):** the private token works as a bearer token. `/v3/events/<id>/` returns `organizer_id`, even for past events. `/v3/organizers/<id>/events/?status=live&expand=venue&order_by=start_asc` lists an organizer's live events, with each venue's name, address and coordinates, `category_id` (103 is music) and `online_event`. Venue pages sometimes link the organizer directly (`eventbrite.com/o/<name>-<id>`), which needs no lookup. Some venues load their Eventbrite links with JavaScript, so the links aren't in the page HTML.

## Goals / Non-Goals

**Goals:**
- More of the venues whose ticketing pages fail get their events, from an official API within its terms.
- The new source behaves like the Ticketmaster one: it's linked by an admin-visible ID, imported unapproved, labelled by kind, and its problems are reported per venue.
- No duplicate events when a venue is reachable more than one way.

**Non-Goals:**
- AXS, Etix and Eventim APIs, which have none that's public.
- SeatGeek, now its own change (`add-seatgeek-source`).
- Paid aggregators such as JamBase. That's for later, if this change's coverage check shows big gaps.
- Searching Eventbrite for venues we don't list.

## Decisions

**A coverage check gated the build.** Task group 1 built the client and a dry-run script, `measure_api_coverage`, which saves nothing and reports per venue whether Eventbrite found its organizer and how many upcoming events it lists. It covered the venues with ticketing-page failures in the last full fetch, and every venue whose platforms include eventbrite, etix or axs.

**Decision (2026-10-26):** with the numbers below in hand, the user chose to build the Eventbrite import now, and to split SeatGeek into its own change rather than wait for its client ID.

**Eventbrite organizers are found through event links, not search.** The venue's pages, which `check_event_sources` already loads, contain `eventbrite.com/e/…-<event id>` links. The matching command fetches the venue's site and events page politely, the same way as the check (same user agent, obeying robots.txt). A page that links an organizer page directly (`eventbrite.com/o/…-<id>`) gives the ID with no lookup. Otherwise it extracts event IDs, calls `/v3/events/<id>/` for up to three of them, and links the venue when their organizers all agree. The organizer's events then come from `/v3/organizers/<id>/events/?status=live&expand=venue,ticket_availability`.

**An organizer whose events are all elsewhere isn't linked.** The coverage run showed a venue's page can link someone else's events: Thirsty Robot Brewery's page led to an organizer with 51 live events, all 13 to 240 km away. So before linking, the command lists the organizer's live events, and when there are some but none is at the venue, it reports the organizer as "events elsewhere" instead. An organizer with no live events at all is still linked, since it may simply be between shows.

An organizer can run events elsewhere, for example a promoter, so each event's venue is compared with ours by name or within 1 km, using `venue_matching`. Events elsewhere are left out and counted in the report.

**One API source per venue, with a fixed precedence.** In `select_targets`, a venue's source becomes the first linked API: Ticketmaster, then Eventbrite. That is, unless its checked source is iCal or JSON-LD, which stay as they are, as with Ticketmaster today. Ticketmaster has the most complete primary data; an Eventbrite organizer is the venue itself selling. Linked venues with no usable saved source are fetched from their API too, as Ticketmaster-linked ones are.

Eventbrite events get the `external_id` prefix `eventbrite:` and the new event source `eventbrite`, so re-fetches update rather than duplicate, and the admin can tell where they came from.

**Events are matched to the venue by name or distance.** An organizer's event counts as at the venue when its Eventbrite venue name matches ours (`names_match`) or it's within 1 km of the venue's location. The coverage run showed the limit of this: Bleacher's Bar's organizer lists its shows at "Bleachers" and "The Midway", 2.7 km from the sheet's town-centre coordinates, because the venue's Places match still needs review. Confirming that match fixes it; matching on Eventbrite's address isn't possible, because Google's terms don't let us store the venue's address.

**Scraped events left behind aren't deleted automatically.** For iCal, removing a venue's unapproved iCal events when Ticketmaster takes over was safe, because the iCal feed is the venue's whole calendar. Scraped ticketing events are messier. Instead, the fetch report notes how many unapproved events from the old source remain, so an admin can tidy them. A later change can automate this once real runs show it's safe.

**Failures use the problem prefixes.** `eventbrite failed:` is added to `PROBLEM_PREFIXES`, so failures appear on the job run and in the venue's fetch status.

**Keys and rate limits.** The client follows `TicketmasterClient`: a session, a minimum interval between requests, and retries on 429 and server errors. The token goes in an `Authorization` header, never a URL, and is never printed.

**Testing and external services:**
- **Eventbrite:** tests use recorded JSON responses in `core/tests/fixtures/eventbrite/`, recorded once with the real API, then the token and personal data stripped. The client gets a fake session that returns them, as `test_ticketmaster.py` does.
- **Venue pages for organizer discovery:** served from small HTML fixtures, with `requests` patched.
- **`fetch_events`:** keeps its fake crawler; tests patch the client's fetch methods.
- **Network:** the suite runs with outbound network blocked.

## Risks / Trade-offs

- [Eventbrite organizer pages include events at other venues.] → Each event's venue is matched, and leftovers are counted in the report.
- [API terms or availability change.] → The API sits behind its own key and links. Clearing the key or the links turns it off without code changes.
- [A venue's page links someone else's organizer.] → Organizers whose live events are all elsewhere aren't linked, and an admin can clear a wrong link.
- [Duplicate events from a venue's old scraped source.] → The precedence prevents new duplicates. Old unapproved ones are reported for an admin to remove.

## Migration Plan

1. One additive migration adds `Venue.eventbrite_organizer_id` and the `eventbrite` event source.
2. Run the matching command with `--dry-run`, then for real.
3. Release through `main`. The links reach Render with the next database copy, or by running the matching command there.

**Rollback:** revert. The fields can stay.

## Open Questions

- **Coverage (answered):** how many failing venues Eventbrite covers.
  - **Measured 2026-10-26, `logs/measure_api_coverage-2026-10-26.log`):** of 83 venues (problem venues from the last full fetch, plus every venue linking Eventbrite, Etix or AXS), an organizer was found for 44, and 32 of those have upcoming events at the venue: 456 events in all. 32 venues have no Eventbrite links in their page HTML, 5 link several organizers, and 2 lookups failed. Two organizers matched no events at the venue (Thirsty Robot: 51 events, 0 matched; Bleacher's Bar: 9, 0 matched); the reasons and what the import does about them are under Decisions.
- **Terms:** do Eventbrite's API terms require attribution or limit caching? This is checked before launch, and it affects only the launch checklist, not this change's code.
