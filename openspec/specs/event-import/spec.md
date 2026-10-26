# event-import Specification

## Purpose
Fetches venues' upcoming events from the source chosen by event-source detection and saves them to the review queue, so re-running it keeps the calendar current without duplicates or overriding admin decisions.

## Requirements

### Requirement: Venues are fetched according to the report
The import SHALL read the saved event-source results and fetch each selected venue from its best source, except that venues linked to Ticketmaster or to an Eventbrite organizer are fetched as `ticketmaster-event-import` and `eventbrite-event-import` describe. A venue with no saved result SHALL be treated as having no usable source. By default it SHALL fetch a small pilot per source. It SHALL fetch every usable venue with `--all`, or named venues with `--sheet-ids`. It SHALL fail clearly when no results have been saved.

#### Scenario: Missing report
- **WHEN** the import runs and no event-source results have been saved
- **THEN** it exits with an error telling the user to run the source check first

#### Scenario: Fetch everything
- **WHEN** the import runs with `--all`
- **THEN** every venue whose best source is ical, json-ld, ticketing or ai-extraction is fetched, and venues with other classifications are not, unless they are linked to Ticketmaster or Eventbrite

#### Scenario: Linked venue with a scrapeable source
- **WHEN** a venue linked to Ticketmaster has best source ical, ticketing or ai-extraction
- **THEN** it is fetched from the Ticketmaster Discovery API only, not also from its report source

#### Scenario: Venue never checked
- **WHEN** the import runs with `--all` and a venue has no saved result and no Ticketmaster or Eventbrite link
- **THEN** that venue is not fetched, and the other venues are

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

#### Scenario: Feed with several timezones in one block
- **WHEN** a feed puts two timezones in one VTIMEZONE block, as the WordPress Events Calendar does
- **THEN** the feed's events are still parsed, with their start times in the timezone each names

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
