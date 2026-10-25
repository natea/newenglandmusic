# ticketmaster-event-import Specification

## Purpose
Imports upcoming music events for venues linked to Ticketmaster from the Ticketmaster Discovery API into the event review queue, as the event source for those venues in place of scraping ticketing pages or AI extraction.

## Requirements

### Requirement: Linked venues are fetched from the Discovery API
When `fetch_events` runs, each venue that has a Ticketmaster venue ID and whose event-source report does not use JSON-LD SHALL get its events from the Discovery API instead of its iCal feed, ticketing-page scraping or AI extraction.

#### Scenario: Linked ticketing venue
- **WHEN** `fetch_events` runs for a linked venue whose report source is ticketing or ai-extraction
- **THEN** its events come from the Discovery API and its pages are not scraped or sent to AI extraction

#### Scenario: Linked venue with structured data
- **WHEN** a linked venue's report source is json-ld
- **THEN** it keeps that source and is not also fetched from the Discovery API

#### Scenario: Linked venue with an iCal feed
- **WHEN** a linked venue's report source is ical
- **THEN** its events come from the Discovery API and its feed is not fetched

#### Scenario: Linked venue missing from the report
- **WHEN** a linked venue has no usable source in the event-source report, e.g. it was bot-blocked
- **THEN** it is still fetched from the Discovery API

### Requirement: Only upcoming music events are imported
The import SHALL request only events starting from now, and SHALL skip events whose primary classification segment is not Music.

#### Scenario: Comedy show at a linked venue
- **WHEN** the API returns an event whose primary segment is Arts & Theatre or Sports
- **THEN** that event is not saved

### Requirement: Imported events are queued for review
Events from the Discovery API SHALL be saved with source `ticketmaster`, matched on an external ID of `tm:` plus the Ticketmaster event ID. New events SHALL be unapproved and existing approvals SHALL be kept.

#### Scenario: First import
- **WHEN** a Ticketmaster event is imported for the first time
- **THEN** it is saved unapproved with source `ticketmaster` and external ID `tm:<event id>`

#### Scenario: Re-import
- **WHEN** the same Ticketmaster event is imported again after an admin approved it
- **THEN** its details are updated, it stays approved, and no duplicate is created

### Requirement: Event fields map from the API response
Each imported event SHALL take its title from the event name, artists from attractions other than one matching the title, start time from the event's start, and both links from the Ticketmaster event URL. Its price SHALL be the bucket of the lowest price, and a description SHALL be escaped.

#### Scenario: Event with a headliner and support
- **WHEN** an event named "Samantha Fish" lists attractions "Samantha Fish" and "Sgt. Splendor" with a lowest price of $35
- **THEN** it is saved with title "Samantha Fish", artists "Sgt. Splendor", price "$$" and the Ticketmaster URL as both its link and its ticket link

#### Scenario: Time not announced
- **WHEN** an event has a start date but no start time
- **THEN** it is saved on that date with its time shown as "time TBA"

### Requirement: Event status is reflected
An event with status `canceled` SHALL be saved as cancelled. A rescheduled event SHALL have its start time updated on re-import.

#### Scenario: Cancelled show
- **WHEN** the API reports an event's status as `canceled`
- **THEN** the saved event is marked cancelled

#### Scenario: Rescheduled show
- **WHEN** a previously imported event comes back with a new start date
- **THEN** the saved event's start time is updated to the new date

### Requirement: Import respects API limits and degrades gracefully
The import SHALL make at most 5 Discovery API requests per second. Without `TICKETMASTER_API_KEY`, or on an API error for a venue, it SHALL skip those venues with a note and the rest of `fetch_events` SHALL complete normally.

#### Scenario: No API key
- **WHEN** `fetch_events` runs without `TICKETMASTER_API_KEY`
- **THEN** linked venues are reported as skipped for Ticketmaster and all other venues are fetched as before

#### Scenario: Rate limited
- **WHEN** the API responds with HTTP 429 for a venue
- **THEN** the request is retried after a back-off, and if it still fails that venue is reported as failed and the run continues

#### Scenario: Dry run
- **WHEN** `fetch_events` runs with `--dry-run`
- **THEN** Ticketmaster events are fetched and reported but nothing is saved

### Requirement: Replaced iCal events are removed
When a linked venue's events are fetched from the Discovery API, its upcoming, unapproved events from its iCal feed SHALL be deleted, so they don't duplicate the Ticketmaster events. Approved events, past events, events from other sources, and dry runs SHALL leave them untouched, and a failed API request SHALL delete nothing.

#### Scenario: Venue switched from iCal
- **WHEN** a linked venue with 3 upcoming unapproved iCal events is fetched from the Discovery API
- **THEN** those 3 events are deleted and the report says so

#### Scenario: Events that are kept
- **WHEN** the venue also has an approved iCal event, a past iCal event and an unapproved Eventbrite event
- **THEN** all three are kept

#### Scenario: API failure
- **WHEN** the Discovery API request for the venue fails
- **THEN** none of its iCal events are deleted
