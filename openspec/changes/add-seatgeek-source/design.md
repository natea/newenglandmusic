## Context

- **Split from `add-eventbrite-seatgeek-sources`** on 2026-10-26. The Eventbrite half, now `add-eventbrite-source`, adds the pattern this follows for a second API: an organizer link on the venue, an `eventbrite` event source, precedence in `fetch_events.select_targets`, and `eventbrite failed:` problem notes.
- **The Ticketmaster pattern:** `match_ticketmaster_venues` links venues using `core/venue_matching.py` (`names_match`, `distance_km`, `spelling_variants`) and its own `find_match`, preferring listings with events. `fetch_ticketmaster` records failures as `ticketmaster failed:` notes, which `is_problem` recognises by prefix.
- **Platform counts from the saved source checks:** etix 21, dice 10, tixr 9, axs 4; the rest are smaller.
- **What the API offers** (SeatGeek's developer docs, read 2026-10-29, and two test requests):
  - a free client ID, sent as a query parameter or by HTTP Basic Auth; the secret is optional
  - `/2/venues`, filtered by `city`, `state`, `postal_code` or `q`, returning `location`, `address` and `url`
  - `/2/events`, filtered by `venue.id` (several IDs separated by commas), `datetime_utc.gte` and `taxonomies.name`, paged by `per_page` and `page`
- **What it doesn't offer:** no ticket listings and no prices; `stats` comes back empty. No images either: public responses leave them out, and the API grants no licence to them. An event's `links` name resale sites (StubHub, RapidSeats) without URLs, and `integrated` names the primary seller (e.g. Ticketmaster) and its event ID, never a link to the Etix or AXS page.
- **`/events` is capped at 10,000 results** from 2026-01-01. SeatGeek recommends its Bulk Catalog API instead: hourly JSONL dumps of events, venues and performers, and a feed of changes from the last hour. Queries for a few venues stay far below the cap.

## Goals / Non-Goals

**Goals:**
- Venues whose ticketing pages fail, and that Ticketmaster and Eventbrite don't cover, get their events from SeatGeek, within its terms.
- SeatGeek behaves like the other API sources: linked by an admin-visible ID, imported unapproved, labelled by kind, with problems reported per venue.
- No duplicate events when a venue is reachable more than one way.

**Non-Goals:**
- Prices. SeatGeek's API returns none, so SeatGeek events have no price bucket.
- Sending people to SeatGeek. Its pages sell resale tickets; see the link decision below.
- SeatGeek's affiliate program (held off on 2026-10-29).
- SeatGeek's images, which the API neither returns nor licenses.
- Searching SeatGeek for venues we don't list.

## Decisions

**A coverage check gates the build.** `measure_api_coverage` gets a SeatGeek check: search the venue by name and state, match with the shared `find_match`, and count its upcoming concerts. The results go into Open Questions and are shown to the user. Groups 2 to 4 are built only if the user wants SeatGeek.

**SeatGeek matching reuses the Ticketmaster rules.** `find_match` is moved into `venue_matching` as a shared function that takes each source's candidate dicts. Both commands call it, so SeatGeek gets the same preference for listings with events, the exact-name rule and the 1 km limit. Concerts are kept by SeatGeek's taxonomy (`concert`, `music_festival`). Other events are counted as left out, as with Ticketmaster's non-music events.

**SeatGeek comes last in the precedence.** A venue's source becomes the first linked API: Ticketmaster, then Eventbrite, then SeatGeek, never over iCal or JSON-LD. SeatGeek is the broadest, but includes resale, so it only fills gaps. Its events get the `external_id` prefix `seatgeek:` and the `seatgeek` event source.

**SeatGeek links are stored, not shown (decided 2026-10-29).** An event's SeatGeek `url` goes in `Event.source_url`, which the site never displays; admins see it on the event. Its `hyperlink` and `ticket_hyperlink` are the venue's own ticket page instead: the venue's events page from its saved source check (`VenueEventSource.events_page`, usually its Etix, AXS or other listing), or else the venue's website. SeatGeek gives no per-event link to the primary seller, so the link is to the venue's listing, not the show. Ticketmaster and Eventbrite events keep linking to the show, since those are the primary sellers.

**Failures and keys.** `seatgeek failed:` is added to `PROBLEM_PREFIXES`. The client follows `TicketmasterClient`. It sends the client ID by HTTP Basic Auth, so the ID is never in a URL, error message or log line. `SEATGEEK_CLIENT_SECRET` is in `.env` but not used: the public endpoints don't need it.

**Testing:** recorded JSON responses in `core/tests/fixtures/seatgeek/` with the client ID stripped, replayed through a fake session; `fetch_events` tests patch the client. The suite runs with outbound network blocked.

## Risks / Trade-offs

- [SeatGeek resells tickets for shows sold elsewhere.] → Its links aren't shown; listings link to the venue's own ticket page.
- [The venue's ticket page is a listing, not the show's page, so people have one more click.] → Accepted. If a SeatGeek event matches the venue's page later, a per-show link can replace it.
- [A venue with no saved events page and no website gets no ticket link.] → The event is saved without one, for an admin to fill in.

## Migration Plan

1. One additive migration adds `Venue.seatgeek_venue_id` and the `seatgeek` event source.
2. Run the coverage check, then `match_seatgeek_venues --dry-run`, then for real.
3. Release through `main`.

**Rollback:** revert. The field can stay.

## Open Questions

- **Coverage:** how many failing venues SeatGeek covers. Answered by task group 1.
- **Terms:** do SeatGeek's API terms require attribution, or limit caching? The developer docs don't say. Checked before launch.
- **Bulk venues file:** would matching from the hourly venues dump be cheaper than a search per venue? Decided in task 2.2, once the coverage numbers show how many venues need matching.
