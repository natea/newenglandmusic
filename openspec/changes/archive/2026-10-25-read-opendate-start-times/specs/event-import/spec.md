# Spec Delta

## ADDED Requirements

### Requirement: Placeholder midnights are checked against OpenDate
When a venue's JSON-LD gives an event a start at exactly midnight Eastern time (00:00 local, or 05:00 UTC), and the event's ticket link is an OpenDate event page, the import SHALL follow that link and use its start time. If the link gives no usable time, the event SHALL be saved as "time TBA". Events at other times SHALL be saved as given.

#### Scenario: Venue site with an OpenDate ticket link
- **WHEN** a venue's JSON-LD gives "Roomful of Blues" a start of 2026-11-06 05:00 UTC, its ticket link is an OpenDate event page, and that page's event data has `start_time` "2026-11-06T20:00:00.000-05:00"
- **THEN** the event is saved starting at 8:00 pm Eastern on November 6

#### Scenario: OpenDate link without a usable time
- **WHEN** a placeholder-midnight event's OpenDate page fails to load, or has no usable `start_time`
- **THEN** the event is saved as all-day on its date, with the time shown as "time TBA"

#### Scenario: Placeholder midnight without an OpenDate link
- **WHEN** a venue's JSON-LD gives an event a start at midnight Eastern, and its ticket link isn't an OpenDate event page
- **THEN** no extra page is requested, and the event is saved as given

#### Scenario: Real time on a venue site
- **WHEN** a venue's JSON-LD gives an event a start at 8:00 pm, with an OpenDate ticket link
- **THEN** no extra page is requested, and the event is saved at 8:00 pm

#### Scenario: Placeholder time filled in on a re-fetch
- **WHEN** a placeholder-midnight event was saved earlier, and a later fetch finds its time on OpenDate
- **THEN** that same event is updated with the time, and no second event is created

## MODIFIED Requirements

### Requirement: JSON-LD events are parsed into events
The import SHALL read schema.org Event nodes anywhere in a page's JSON-LD, including nested and list nodes. It SHALL take performers other than the title as artists, the first offer price as the price, and the offer URL as the ticket link. It SHALL treat a date-only `startDate` as an all-day event with the time shown as "time TBA".

#### Scenario: Event with performers and offers
- **WHEN** a MusicEvent named "Samantha Fish" lists performers "Samantha Fish" and "Sgt. Splendor" and an offer of $25 with a URL
- **THEN** it is saved with artists "Sgt. Splendor", price "$" and that ticket link

#### Scenario: Invalid JSON-LD block
- **WHEN** one JSON-LD script on the page is not valid JSON
- **THEN** it is ignored and events in the page's other blocks are still read

#### Scenario: Date-only start
- **WHEN** an Event node's `startDate` is "2026-11-06", with no time
- **THEN** the event is saved on November 6 as all-day, with the time shown as "time TBA"

### Requirement: Ticketing-platform event pages are followed
For ticketing venues, the import SHALL follow up to 10 event links per page that point to known ticketing platforms. It SHALL read their JSON-LD and send pages without structured data for AI extraction. On an OpenDate event page whose JSON-LD gives only a date, it SHALL take the start time from the page's own event data when that time falls on the same local date. Filling in the time SHALL NOT change the event's identity.

#### Scenario: Platform page without structured data
- **WHEN** a linked ticketing event page has no JSON-LD events
- **THEN** its text is sent for AI extraction

#### Scenario: OpenDate page with a start time
- **WHEN** an OpenDate event page's JSON-LD has `startDate` "2026-11-06", and its event data has `start_time` "2026-11-06T22:00:00.000-05:00"
- **THEN** the event is saved starting at 10:00 pm Eastern on November 6, not as all-day

#### Scenario: OpenDate page without usable event data
- **WHEN** an OpenDate event page's JSON-LD has a date-only `startDate`, and its event data is missing, isn't valid JSON, has no `start_time`, or has a `start_time` on a different local date
- **THEN** the event is saved as all-day on the JSON-LD date, with the time shown as "time TBA"

#### Scenario: Time filled in on a re-fetch
- **WHEN** an OpenDate event was saved earlier as "time TBA", and a later fetch finds its start time
- **THEN** that same event is updated with the time, and no second event is created
