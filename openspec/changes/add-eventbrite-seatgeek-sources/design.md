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
- **What the APIs offer** (from third-party documentation, to be confirmed in task group 1):
  - **Eventbrite:** a private token, from the account's API Keys page, is sent as a bearer token. The public event search is retired, so events are reached through known IDs: an event's details give its `organizer_id`, and an organizer's events can be listed.
  - **SeatGeek:** a free client ID, passed as a query parameter. It offers `/2/venues` (search by name and location) and `/2/events?venue.id=…`, with taxonomies that tell concerts apart from other events.

**Checked against the real Eventbrite API (2026-10-26):** the private token works as a bearer token. `/v3/events/<id>/` returns `organizer_id`, even for past events. `/v3/organizers/<id>/events/?status=live&expand=venue&order_by=start_asc` lists an organizer's live events, with each venue's name, address and coordinates, `category_id` (103 is music) and `online_event`. Venue pages sometimes link the organizer directly (`eventbrite.com/o/<name>-<id>`), which needs no lookup. Some venues load their Eventbrite links with JavaScript, so the links aren't in the page HTML.

## Goals / Non-Goals

**Goals:**
- More of the venues whose ticketing pages fail get their events, from official APIs within their terms.
- Each new source behaves like the Ticketmaster one: it's linked by an admin-visible ID, imported unapproved, labelled by kind, and its problems are reported per venue.
- No duplicate events when a venue is reachable more than one way.

**Non-Goals:**
- AXS, Etix and Eventim APIs, which have none that's public.
- Paid aggregators such as JamBase. That's for later, if this change's coverage check shows big gaps.
- Searching Eventbrite or SeatGeek for venues we don't list.
- Resale prices. SeatGeek's price fields may reflect resale listings, so they're used only for the price bucket, as Ticketmaster's are.

## Decisions

**A coverage check gates the build.** Task group 1 builds the two clients and a dry-run script, `measure_api_coverage`. It doesn't save anything, and reports per venue whether each API found it and how many upcoming events it lists. It covers:
- the venues with ticketing-page failures in the last full fetch
- every venue whose platforms include eventbrite, etix or axs

The script's results go into this design's Open Questions section and get shown to the user. Groups 2 to 4 are built only for an API the user wants to keep. Dropping one removes its tasks, and its spec file, from this change.

**Eventbrite organizers are found through event links, not search.** The venue's pages, which `check_event_sources` already loads, contain `eventbrite.com/e/…-<event id>` links. The matching command fetches the venue's site and events page politely, the same way as the check (same user agent, obeying robots.txt). It extracts event IDs, calls `/v3/events/<id>/` for each `organizer_id`, and links the venue when they all agree. The organizer's events then come from `/v3/organizers/<id>/events/?status=live&expand=venue`.

An organizer can run events elsewhere, for example a promoter, so each event's venue is compared with ours by name or within 1 km, using `venue_matching`. Events elsewhere are left out and counted in the report.

**SeatGeek matching reuses the Ticketmaster rules.** `find_match` in `match_ticketmaster_venues` is moved into `venue_matching` as a shared function, and takes each source's candidate dicts. Both commands call it, so SeatGeek gets the same preference for listings with events, plus the exact-name rule and the 1 km limit. Concerts are kept by SeatGeek's taxonomy (`concert`, `music_festival`). Other events are counted as left out, as with Ticketmaster's non-music events.

**One API source per venue, with a fixed precedence.** In `select_targets`, a venue's source becomes the first linked API: Ticketmaster, then Eventbrite, then SeatGeek. That is, unless its checked source is iCal or JSON-LD, which stay as they are, as with Ticketmaster today. The reasoning:
- Ticketmaster has the most complete primary data.
- An Eventbrite organizer is the venue itself selling.
- SeatGeek is the broadest, but includes resale, so it comes last.

Each API's events get an `external_id` prefix (`eventbrite:` or `seatgeek:`), so re-fetches update rather than duplicate.

**Scraped events left behind aren't deleted automatically.** For iCal, removing a venue's unapproved iCal events when Ticketmaster takes over was safe, because the iCal feed is the venue's whole calendar. Scraped ticketing events are messier. Instead, the fetch report notes how many unapproved events from the old source remain, so an admin can tidy them. A later change can automate this once real runs show it's safe.

**Failures use the problem prefixes.** `eventbrite failed:` and `seatgeek failed:` are added to `PROBLEM_PREFIXES`, so failures appear on the job run and in the venue's fetch status.

**Keys and rate limits.** Both clients follow `TicketmasterClient`: a session, a minimum interval between requests, and the key passed as the API expects. Eventbrite's token goes in an `Authorization` header. SeatGeek's client ID goes in the query string, which the API requires, so the client strips it from any error message or log line. Keys are never printed.

**Testing and external services:**
- **Eventbrite and SeatGeek:** tests use recorded JSON responses in `core/tests/fixtures/eventbrite/` and `core/tests/fixtures/seatgeek/`. They're recorded once with the real APIs, then any token, client ID and personal data are stripped. The clients get a fake session that returns them, as `test_ticketmaster.py` does.
- **Venue pages for organizer discovery:** served from small HTML fixtures, with `requests` patched.
- **`fetch_events`:** keeps its fake crawler; tests patch the two clients' fetch methods.
- **Network:** the suite runs with outbound network blocked.

## Risks / Trade-offs

- [SeatGeek lists resale tickets for shows sold elsewhere, so its links may point people to resale.] → It's last in precedence, its events link to SeatGeek's event page, and its terms are checked before launch. If that's unacceptable, it can be limited to venues with no other source.
- [Eventbrite organizer pages include events at other venues.] → Each event's venue is matched, and leftovers are counted in the report.
- [API terms or availability change.] → Each API sits behind its own key and link. Clearing the key or the links turns it off without code changes.
- [Duplicate events from a venue's old scraped source.] → The precedence prevents new duplicates. Old unapproved ones are reported for an admin to remove.

## Migration Plan

1. One additive migration adds the two `Venue` fields.
2. Run the coverage check locally, then the matching commands with `--dry-run`, then for real.
3. Release through `main`. The links reach Render with the next database copy, or by running the matching commands there.

**Rollback:** revert. The fields can stay.

## Open Questions

- **Coverage:** how many failing venues each API covers. Answered by task group 1, and it decides whether groups 2 to 4 are built for each API.
  - **Eventbrite (measured 2026-10-26, `logs/measure_api_coverage-2026-10-26.log`):** of 83 venues (problem venues from the last full fetch, plus every venue linking Eventbrite, Etix or AXS), an organizer was found for 44, and 32 of those have upcoming events at the venue: 456 events in all. 32 venues have no Eventbrite links in their page HTML, 5 link several organizers, and 2 lookups failed. Some organizers' events don't match the venue by name or within 1 km (Thirsty Robot: 51 events, 0 matched; Bleacher's Bar: 9, 0 matched), which the import's matching should look at.
  - **SeatGeek:** not measured yet; waiting for a client ID.
- **Terms:** do Eventbrite's and SeatGeek's API terms require attribution or limit caching? These are checked before launch, and they affect only the launch checklist, not this change's code.
