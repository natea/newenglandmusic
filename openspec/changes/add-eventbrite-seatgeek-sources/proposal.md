## Why

Many venues sell through ticketing platforms whose pages refuse our crawler. In the last full fetch, TicketWeb, AXS, Etix, Eventbrite and Eventim pages failed at 12 venues. Ticketmaster solved this for venues it lists, through its official API, and moving four TicketWeb venues onto it today brought in 35 events their pages wouldn't give.

AXS, Etix and Eventim offer no public listings API. But two free official APIs could cover much of the gap:
- **Eventbrite:** 57 of our venues link to Eventbrite and aren't linked to Ticketmaster.
- **SeatGeek:** it lists shows across many primary sellers, so it may cover the 21 Etix and 4 AXS venues, and others.

## What Changes

- **A measured coverage check comes first.** A dry-run script tries both APIs on the venues that failed, and on the Eventbrite, Etix and AXS venues, and reports how many each could cover. The rest of this change goes ahead only for an API that covers enough venues. The user decides, with the numbers in hand.
- **Eventbrite organizer links:**
  - A venue can be linked to its Eventbrite organizer ID.
  - A matching command finds the ID from Eventbrite event links on the venue's own pages, through the Eventbrite API's event details.
  - `fetch_events` fetches the organizer's live events, keeping only those at the venue, and saves them like any other import: unapproved, matched on external ID, and labelled by kind.
- **SeatGeek venue links:**
  - A venue can be linked to a SeatGeek venue ID.
  - A matching command finds it by name and distance, the way `match_ticketmaster_venues` does.
  - `fetch_events` fetches that venue's upcoming concerts.
- **One API source per venue:** a venue linked to several APIs is fetched from one, in this order: Ticketmaster, then Eventbrite, then SeatGeek. Like Ticketmaster today, a linked API replaces the venue's ticketing-page scraping and AI extraction, but not its iCal feed or JSON-LD. This avoids the same show being saved twice under different IDs.
- **Admin:** both IDs are editable on the venue page, searchable, and filterable ("linked to Eventbrite", "linked to SeatGeek").
- **Keys:** the new settings `EVENTBRITE_TOKEN` and `SEATGEEK_CLIENT_ID`, read from `.env`, are listed in `.env.example` and `PRODUCTION.md`. A missing key skips that API with a note, as with Ticketmaster.

## Capabilities

### New Capabilities

- `eventbrite-event-import`: linking venues to Eventbrite organizers and importing their events from the Eventbrite API.
- `seatgeek-event-import`: linking venues to SeatGeek venues and importing their events from the SeatGeek API.

### Modified Capabilities

None for now. `event-import`'s "Venues are fetched according to the report" requirement will need a mention of the new API sources. A pending, unarchived change (`store-event-sources-in-db`) already modifies it, so that wording is updated when this change is archived, after that one.

## Impact

- **Models:**
  - `Venue.eventbrite_organizer_id` and `Venue.seatgeek_venue_id`, both blank by default and not synced from the sheet
  - one migration
- **Code:**
  - new clients `core/event_fetching/eventbrite.py` and `core/event_fetching/seatgeek.py`, modelled on `ticketmaster.py`
  - new commands `match_eventbrite_organizers` and `match_seatgeek_venues`
  - `fetch_events` target selection and fetching
- **Tests:** recorded API responses with the keys stripped, in `core/tests/fixtures/eventbrite/` and `core/tests/fixtures/seatgeek/`, and mocked clients. No network.
- **External services:** two new free APIs. The user creates the Eventbrite account token and the SeatGeek client ID. Their terms on attribution and caching are checked before launch.
