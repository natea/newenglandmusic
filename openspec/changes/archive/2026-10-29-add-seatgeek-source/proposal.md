## Why

Many venues sell through ticketing platforms whose pages refuse our crawler, and AXS, Etix and Eventim offer no public listings API. SeatGeek lists shows across many primary sellers, so its free official API may cover the 21 Etix and 4 AXS venues, and others that neither Ticketmaster nor Eventbrite reaches.

This was half of `add-eventbrite-seatgeek-sources`. It was split out on 2026-10-26, while SeatGeek approved the developer account, and the Eventbrite half (`add-eventbrite-source`) went ahead and is archived. SeatGeek approved the account on 2026-10-29, and the client ID works.

SeatGeek's API gives event details only: no ticket listings and no prices (SeatGeek's email of 2026-10-29, and an empty `stats` on real events). Its event links go to SeatGeek, which resells tickets.

## What Changes

- **A measured coverage check comes first.** `measure_api_coverage` gains a SeatGeek check, and is run on the same venues as Eventbrite's. The rest of this change goes ahead only if SeatGeek covers enough venues. The user decides, with the numbers in hand.
- **SeatGeek venue links:**
  - A venue can be linked to a SeatGeek venue ID.
  - A matching command finds it by name and distance, the way `match_ticketmaster_venues` does.
  - `fetch_events` fetches that venue's upcoming concerts.
- **Precedence:** SeatGeek comes last, after Ticketmaster and Eventbrite. Like them, it replaces the venue's ticketing-page scraping and AI extraction, but not its iCal feed. It replaces a venue's JSON-LD only in a run where SeatGeek has more concerts than the JSON-LD found upcoming events, since some venues' JSON-LD is a single show's page.
- **Links:** a SeatGeek event's own SeatGeek link is stored, but not shown, so nobody is sent to resale. Instead each event links, in order of preference, to:
  1. **the show's own page** on Etix or AXS, found among the links on the venue's own events page by the show's title (e.g. `etix.com/ticket/p/96934398/as-i-lay-dying-…`), so people buy straight from the venue's seller;
  2. else **the venue's ticket page**, its list of shows on Etix or AXS (e.g. `etix.com/ticket/v/677`). It's a new field on the venue, which editors can set, and which is filled in automatically from the venue's own site when blank;
  3. else the venue's website.

  SeatGeek events have no price.
- **Admin:** the SeatGeek venue ID is editable on the venue page, searchable, and filterable ("linked to SeatGeek").
- **Key:** the new setting `SEATGEEK_CLIENT_ID`, read from `.env`, is listed in `.env.example` and `PRODUCTION.md`, and sent by HTTP Basic Auth, never in a URL. The client secret isn't needed for these endpoints. A missing key skips SeatGeek with a note.

## Capabilities

### New Capabilities

- `seatgeek-event-import`: linking venues to SeatGeek venues and importing their events from the SeatGeek API.

### Modified Capabilities

None. Eventbrite's spec already gives Ticketmaster precedence over Eventbrite, and this change's own spec puts SeatGeek after both.

## Impact

- **Builds on** `add-eventbrite-source` (archived 2026-10-26), for the precedence in `fetch_events` and the shared coverage command.
- **Models:** `Venue.seatgeek_venue_id` and `Venue.ticket_page_url`, blank by default and not synced from the sheet; `Event.Source.SEATGEEK`; one migration.
- **Code:**
  - a new client `core/event_fetching/seatgeek.py`, modelled on `ticketmaster.py`
  - `find_match` moved from `match_ticketmaster_venues` into `core/venue_matching.py`, shared by both matching commands
  - a new command `match_seatgeek_venues`
  - `fetch_events` target selection and fetching; `measure_api_coverage`
  - a new module `core/event_fetching/ticket_links.py` that finds Etix and AXS show and venue links on a venue's page, and matches shows to them by title
  - the event admin shows each event's source, source page and external ID, and filters by source
- **Tests:** recorded API responses with the client ID stripped, in `core/tests/fixtures/seatgeek/`, and mocked clients. No network.
- **External services:** the free SeatGeek API. Its terms on attribution and caching are checked before launch. The SeatGeek affiliate program is left out for now.
