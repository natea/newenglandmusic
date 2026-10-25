# Spec Delta

## Purpose

Fetches venues' upcoming events from the source chosen by event-source detection and saves them to the review queue, so re-running it keeps the calendar current without duplicates or overriding admin decisions.

## ADDED Requirements

### Requirement: Venues are fetched according to the report
The import SHALL read the event-source report and fetch each selected venue from its best source. By default it SHALL fetch a small pilot per source. It SHALL fetch every usable venue with `--all`, or named venues with `--sheet-ids`. It SHALL fail clearly when the report is missing.

#### Scenario: Missing report
- **WHEN** the import runs and the report file doesn't exist
- **THEN** it exits with an error telling the user to run the source check first

#### Scenario: Fetch everything
- **WHEN** the import runs with `--all`
- **THEN** every venue whose best source is ical, json-ld, ticketing or ai-extraction is fetched, and venues with other classifications are not

### Requirement: iCal feeds are parsed into events
The import SHALL turn each VEVENT in a venue's feed into an event. It SHALL use its summary, start, description, URL and cancelled status, and SHALL treat date-only starts as all-day events with the time shown as "time TBA".

#### Scenario: Cancelled feed entry
- **WHEN** a VEVENT has STATUS:CANCELLED
- **THEN** the saved event is marked cancelled

#### Scenario: Recurring event instances
- **WHEN** a feed has several instances sharing one UID at different start times
- **THEN** each instance is saved as a separate event

#### Scenario: Malformed feed
- **WHEN** a venue's feed can't be parsed
- **THEN** the venue's events page is sent for AI extraction instead and the fallback is reported

### Requirement: JSON-LD events are parsed into events
The import SHALL read schema.org Event nodes anywhere in a page's JSON-LD, including nested and list nodes. It SHALL take performers other than the title as artists, the first offer price as the price, and the offer URL as the ticket link.

#### Scenario: Event with performers and offers
- **WHEN** a MusicEvent named "Samantha Fish" lists performers "Samantha Fish" and "Sgt. Splendor" and an offer of $25 with a URL
- **THEN** it is saved with artists "Sgt. Splendor", price "$" and that ticket link

#### Scenario: Invalid JSON-LD block
- **WHEN** one JSON-LD script on the page is not valid JSON
- **THEN** it is ignored and events in the page's other blocks are still read

### Requirement: Ticketing-platform event pages are followed
For ticketing venues, the import SHALL follow up to 10 event links per page that point to known ticketing platforms. It SHALL read their JSON-LD and send pages without structured data for AI extraction.

#### Scenario: Platform page without structured data
- **WHEN** a linked ticketing event page has no JSON-LD events
- **THEN** its text is sent for AI extraction

### Requirement: Placeholder entries are not events
The import SHALL skip entries whose title marks the absence of an event, such as "No Event Tonight", "No Shows" or "Closed".

#### Scenario: Placeholder in a feed
- **WHEN** a feed entry is titled "No Event Tonight"
- **THEN** it is not saved

### Requirement: Only upcoming events are saved, and at most 50 per venue
The import SHALL save only events starting from now onward. It SHALL deduplicate events found on more than one page by external ID, and SHALL save at most the 50 soonest per venue.

#### Scenario: Past events in a feed
- **WHEN** a feed contains last month's shows
- **THEN** they are not saved

### Requirement: Imported events are queued for review without duplicates
Each event SHALL get an external ID from its source. A new event SHALL be saved unapproved. An event with an existing external ID SHALL be updated in place, keeping its approval.

#### Scenario: Re-running the import
- **WHEN** the import runs twice over the same feed
- **THEN** no duplicates are created and the second run reports the events as updated

#### Scenario: Previously approved event
- **WHEN** an approved event is re-imported with a changed description
- **THEN** its description changes and it stays approved

### Requirement: Imported content is safe to display
Descriptions from venue websites SHALL be stripped of HTML, unescaped, shortened to 600 characters and HTML-escaped before saving. Text fields that don't fit SHALL be left empty instead of failing the save.

#### Scenario: Script in a description
- **WHEN** a source description contains `<script>alert(1)</script>`
- **THEN** the saved description contains no executable markup

#### Scenario: Over-long URL
- **WHEN** an event's link is longer than 255 characters
- **THEN** the event is saved with no link instead of failing

### Requirement: Prices map to the site's price ranges
The import SHALL map a numeric price to the site's buckets: 0 is "free", under 30 is "$", under 50 is "$$", under 75 is "$$$", and anything higher is "$$$$". No price SHALL mean no bucket.

#### Scenario: $35 ticket
- **WHEN** an event's lowest price is 35
- **THEN** it is saved with price "$$"

### Requirement: Crawling is polite
The import SHALL obey robots.txt, use the same honest user agent as the source check, throttle requests per domain, and report requests that fail without stopping the run.

#### Scenario: Request fails
- **WHEN** one venue's page times out
- **THEN** that failure appears in the report under the venue and other venues are still imported

### Requirement: Dry runs save nothing
With `--dry-run`, the import SHALL fetch and report as usual but save nothing.

#### Scenario: Dry run
- **WHEN** the import runs with `--dry-run`
- **THEN** the report shows what would be created and updated, and the database is unchanged
