## Context

- **Split from `add-eventbrite-seatgeek-sources`** on 2026-10-26. The Eventbrite half, now `add-eventbrite-source`, adds the pattern this follows for a second API: an organizer link on the venue, an `eventbrite` event source, precedence in `fetch_events.select_targets`, and `eventbrite failed:` problem notes.
- **The Ticketmaster pattern:** `match_ticketmaster_venues` links venues using `core/venue_matching.py` (`names_match`, `distance_km`, `spelling_variants`) and its own `find_match`, preferring listings with events. `fetch_ticketmaster` records failures as `ticketmaster failed:` notes, which `is_problem` recognises by prefix.
- **Platform counts from the saved source checks:** etix 21, dice 10, tixr 9, axs 4; the rest are smaller.
- **What the API offers** (from third-party documentation, to be confirmed in task group 1): a free client ID, passed as a query parameter. It offers `/2/venues` (search by name and location) and `/2/events?venue.id=…`, with taxonomies that tell concerts apart from other events.

## Goals / Non-Goals

**Goals:**
- Venues whose ticketing pages fail, and that Ticketmaster and Eventbrite don't cover, get their events from SeatGeek, within its terms.
- SeatGeek behaves like the other API sources: linked by an admin-visible ID, imported unapproved, labelled by kind, with problems reported per venue.
- No duplicate events when a venue is reachable more than one way.

**Non-Goals:**
- Resale prices. SeatGeek's price fields may reflect resale listings, so they're used only for the price bucket, as Ticketmaster's are.
- Searching SeatGeek for venues we don't list.

## Decisions

**A coverage check gates the build.** `measure_api_coverage` gets a SeatGeek check: search the venue by name and state, match with the shared `find_match`, and count its upcoming concerts. The results go into Open Questions and are shown to the user. Groups 2 to 4 are built only if the user wants SeatGeek.

**SeatGeek matching reuses the Ticketmaster rules.** `find_match` is moved into `venue_matching` as a shared function that takes each source's candidate dicts. Both commands call it, so SeatGeek gets the same preference for listings with events, the exact-name rule and the 1 km limit. Concerts are kept by SeatGeek's taxonomy (`concert`, `music_festival`). Other events are counted as left out, as with Ticketmaster's non-music events.

**SeatGeek comes last in the precedence.** A venue's source becomes the first linked API: Ticketmaster, then Eventbrite, then SeatGeek, never over iCal or JSON-LD. SeatGeek is the broadest, but includes resale, so it only fills gaps. Its events get the `external_id` prefix `seatgeek:` and the `seatgeek` event source.

**Failures and keys.** `seatgeek failed:` is added to `PROBLEM_PREFIXES`. The client follows `TicketmasterClient`. The client ID has to go in the query string, so the client strips it from any error message or log line, and it is never printed.

**Testing:** recorded JSON responses in `core/tests/fixtures/seatgeek/` with the client ID stripped, replayed through a fake session; `fetch_events` tests patch the client. The suite runs with outbound network blocked.

## Risks / Trade-offs

- [SeatGeek lists resale tickets for shows sold elsewhere, so its links may point people to resale.] → It's last in precedence, its events link to SeatGeek's event page, and its terms are checked before launch. If that's unacceptable, it can be limited to venues with no other source.
- [Approval may never come.] → Nothing else depends on this change; it can be dropped.

## Migration Plan

1. One additive migration adds `Venue.seatgeek_venue_id` and the `seatgeek` event source.
2. Run the coverage check, then `match_seatgeek_venues --dry-run`, then for real.
3. Release through `main`.

**Rollback:** revert. The field can stay.

## Open Questions

- **Coverage:** how many failing venues SeatGeek covers. Answered by task group 1, once the client ID arrives.
- **Terms:** do SeatGeek's API terms require attribution, or limit caching or links to resale? Checked before launch.
