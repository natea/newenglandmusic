## Why

Many venues sell through ticketing platforms whose pages refuse our crawler, and AXS, Etix and Eventim offer no public listings API. SeatGeek lists shows across many primary sellers, so its free official API may cover the 21 Etix and 4 AXS venues, and others that neither Ticketmaster nor Eventbrite reaches.

This was half of `add-eventbrite-seatgeek-sources`. It was split out on 2026-10-26, because SeatGeek hasn't yet approved the client ID the API needs, while the Eventbrite half (`add-eventbrite-source`) went ahead.

## What Changes

- **A measured coverage check comes first.** `measure_api_coverage` gains a SeatGeek check, and is run on the same venues as Eventbrite's. The rest of this change goes ahead only if SeatGeek covers enough venues. The user decides, with the numbers in hand.
- **SeatGeek venue links:**
  - A venue can be linked to a SeatGeek venue ID.
  - A matching command finds it by name and distance, the way `match_ticketmaster_venues` does.
  - `fetch_events` fetches that venue's upcoming concerts.
- **Precedence:** SeatGeek comes last, after Ticketmaster and Eventbrite. Like them, it replaces the venue's ticketing-page scraping and AI extraction, but not its iCal feed or JSON-LD.
- **Admin:** the SeatGeek venue ID is editable on the venue page, searchable, and filterable ("linked to SeatGeek").
- **Key:** the new setting `SEATGEEK_CLIENT_ID`, read from `.env`, is listed in `.env.example` and `PRODUCTION.md`. A missing key skips SeatGeek with a note.

## Capabilities

### New Capabilities

- `seatgeek-event-import`: linking venues to SeatGeek venues and importing their events from the SeatGeek API.

### Modified Capabilities

- `eventbrite-event-import` (once `add-eventbrite-source` is archived): the one-source-per-venue rule extends to SeatGeek. Until then, the precedence is stated in this change's own spec.

## Impact

- **Depends on** `add-eventbrite-source`, for the precedence in `fetch_events` and the shared coverage command.
- **Models:** `Venue.seatgeek_venue_id`, blank by default and not synced from the sheet; `Event.Source.SEATGEEK`; one migration.
- **Code:**
  - a new client `core/event_fetching/seatgeek.py`, modelled on `ticketmaster.py`
  - `find_match` moved from `match_ticketmaster_venues` into `core/venue_matching.py`, shared by both matching commands
  - a new command `match_seatgeek_venues`
  - `fetch_events` target selection and fetching; `measure_api_coverage`
- **Tests:** recorded API responses with the client ID stripped, in `core/tests/fixtures/seatgeek/`, and mocked clients. No network.
- **External services:** the free SeatGeek API. The user gets the client ID. Its terms on attribution, resale links and caching are checked before launch.
