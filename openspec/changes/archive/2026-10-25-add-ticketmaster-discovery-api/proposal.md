# Proposal

## Why

23 venues in the sheet sell tickets through Ticketmaster or Live Nation, and 16 of them had no upcoming events after the last full `fetch_events --all` run. Two things cause this. Ticketmaster's event pages block automated requests. Many of these venues' own sites, such as the Crossroads Presents pages for Paradise Rock Club, MGM Music Hall, the Orpheum and Brighton Music Hall, load their listings with JavaScript. These are some of the largest rooms in the region. Ticketmaster's official Discovery API returns their events as structured data: dates, times, price ranges, performers and status. It is free, needs only an API key, and it is the route Ticketmaster allows.

## What Changes

- **Link venues to Ticketmaster.** Each venue can store the ID of its matching Ticketmaster venue. A new command finds candidates through the Discovery API's venue search. It links a venue automatically only when the name and location clearly match, and it reports ambiguous matches for an admin to settle. Admins can also set or clear the link by hand.
- **Import events from the API.** For linked venues, `fetch_events` gets upcoming events from the Discovery API in place of scraping the ticketing pages or using AI extraction. These events are saved like other imported events: unapproved, matched on a stable external ID so re-runs update them, and with existing approvals kept.
- **Add a new event source, `ticketmaster`,** alongside ical, json-ld, ticketing and ai.
- **Only import music events.** Non-music events at linked venues, such as comedy, sports and family shows, are skipped.
- **Mark cancelled events** as cancelled, and update the date of rescheduled events.
- **Read the API key from `TICKETMASTER_API_KEY`.** Without the key, the Ticketmaster step is skipped with a note and the rest of `fetch_events` runs as it does today.
- **Stay within the API's limits** of 5 requests per second and 5,000 per day.
- **Not breaking.** Venues without a Ticketmaster link behave exactly as before.

## Capabilities

### New Capabilities

- `ticketmaster-venue-linking`: matches venues in the database to Ticketmaster venues, stores the link, and reports matches that need a person to decide.
- `ticketmaster-event-import`: imports upcoming music events for linked venues from the Discovery API into the event review queue.

### Modified Capabilities

- `event-import`: venues linked to Ticketmaster are fetched from the Discovery API in place of their ticketing or AI source, and are fetched even when the report gave them no usable source.

## Impact

- **Model:**
  - `Venue` gains a nullable `ticketmaster_venue_id`. `sync_venues_from_gsheets` does not manage this field, so a sheet sync leaves it alone.
  - `Event.source` gains the `ticketmaster` choice.
  - Both changes need one migration.
- **Code:**
  - A new module, `core/event_fetching/ticketmaster.py`, holds the API client and maps API events to the event dicts that `save_event` already accepts.
  - A new management command, `match_ticketmaster_venues`.
  - `fetch_events` picks its targets and fetches events differently for linked venues.
  - The venue admin gets the new field and a filter.
- **Configuration:** `.env` and `.env.example` gain `TICKETMASTER_API_KEY`.
- **Dependencies:** none new. `requests` is already installed.
- **External:** this adds a dependency on the Ticketmaster Discovery API and its Partner API Terms, which must be reviewed before any public deployment. The project is local only for now.
