## Why

Many venues sell through ticketing platforms whose pages refuse our crawler. In the last full fetch, TicketWeb, AXS, Etix, Eventbrite and Eventim pages failed at 12 venues. Ticketmaster solved this for venues it lists, through its official API, and moving four TicketWeb venues onto it brought in 35 events their pages wouldn't give.

Eventbrite has a free official API, and 57 of our venues link to Eventbrite without being on Ticketmaster. A measured coverage check (2026-10-26) found an Eventbrite organizer for 44 of 83 venues checked, 32 of them with upcoming events at the venue: 456 events in all.

SeatGeek, the other free API considered, is waiting on SeatGeek's approval of a client ID. It is split out into its own change, `add-seatgeek-source`.

## What Changes

- **A measured coverage check came first** (`measure_api_coverage`, done). The user chose to build the Eventbrite import on its numbers.
- **Eventbrite organizer links:**
  - A venue can be linked to its Eventbrite organizer ID.
  - A matching command finds the ID from the Eventbrite links on the venue's own pages: organizer page links directly, or event links through the Eventbrite API's event details. It doesn't link an organizer whose live events are all at other venues.
  - `fetch_events` fetches the organizer's live events, keeping only those at the venue, and saves them like any other import: unapproved, matched on external ID, and labelled by kind.
- **One API source per venue:** a venue linked to both Ticketmaster and Eventbrite is fetched from Ticketmaster. Like Ticketmaster, Eventbrite replaces the venue's ticketing-page scraping and AI extraction, but not its iCal feed or JSON-LD. This avoids the same show being saved twice under different IDs.
- **Admin:** the organizer ID is editable on the venue page, searchable, and filterable ("linked to Eventbrite").
- **Key:** `EVENTBRITE_API_KEY`, read from `.env`, is listed in `.env.example` and `PRODUCTION.md`. A missing key skips Eventbrite with a note, as with Ticketmaster.

## Capabilities

### New Capabilities

- `eventbrite-event-import`: linking venues to Eventbrite organizers and importing their events from the Eventbrite API.

### Modified Capabilities

None for now. `event-import`'s "Venues are fetched according to the report" requirement will need a mention of the new API source; it is updated when this change is archived.

## Impact

- **Models:**
  - `Venue.eventbrite_organizer_id`, blank by default and not synced from the sheet
  - `Event.Source.EVENTBRITE`
  - one migration
- **Code:**
  - the client `core/event_fetching/eventbrite.py` (done) and `measure_api_coverage` (done)
  - the new command `match_eventbrite_organizers`
  - `fetch_events` target selection and fetching
- **Tests:** recorded API responses with the token stripped, in `core/tests/fixtures/eventbrite/`, and mocked clients. No network.
- **External services:** the free Eventbrite API, with the user's private token. Its terms on attribution and caching are checked before launch.
