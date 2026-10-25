# Spec Delta

## Purpose

Works out, for each venue, whether its upcoming events can be fetched and from which kind of source, and records the answer in a report that event import reads.

## ADDED Requirements

### Requirement: Each checked venue gets one best source
The check SHALL classify each venue's best source, preferring a verified iCal feed, then schema.org JSON-LD events, then ticketing-platform links, and otherwise AI extraction of a page that loads.

#### Scenario: Site with a working feed and JSON-LD
- **WHEN** a venue's pages link an iCal feed that contains at least one event and also embed JSON-LD events
- **THEN** its best source is ical, with the feed URL and its event count recorded

#### Scenario: Linked feed that isn't a calendar
- **WHEN** a linked .ics URL does not return a calendar with events
- **THEN** it is not used as the venue's feed

#### Scenario: WordPress Events Calendar site
- **WHEN** a page uses the WordPress Events Calendar plugin without linking a feed
- **THEN** the site's `/events/?ical=1` feed is tried

#### Scenario: Ticketing links only
- **WHEN** a venue has no feed or JSON-LD events but links to a known ticketing platform
- **THEN** its best source is ticketing and the platforms found are recorded

#### Scenario: Plain listing page
- **WHEN** a page loads but has none of the above
- **THEN** its best source is ai-extraction

### Requirement: Venues that can't be checked are classified by reason
The check SHALL record a reason instead of a source: no-website, social-only (Facebook, Instagram or Linktree), robots-blocked, dead-domain (the domain doesn't resolve), bot-blocked (HTTP 403, 406 or 429), unreachable, or check-failed (an unexpected error, which SHALL NOT stop the run).

#### Scenario: Social-only venue
- **WHEN** a venue's only URL is a Facebook page
- **THEN** it is reported as social-only and not fetched

#### Scenario: Site that refuses the crawler
- **WHEN** a site answers HTTP 403
- **THEN** the venue is reported as bot-blocked with the error

#### Scenario: robots.txt disallows the crawler
- **WHEN** robots.txt disallows the check's user agent for the venue's URL
- **THEN** the page is not fetched and the venue is reported as robots-blocked

#### Scenario: Unexpected error
- **WHEN** checking one venue raises an unexpected exception
- **THEN** that venue is reported as check-failed with the error and the other venues are still checked

### Requirement: The events listing page is found
The check SHALL look for a link to the site's events listing and SHALL prefer navigation links named like "Events", "Shows" or "Calendar". It SHALL skip private-event or rental pages, single-event pages and file links, and SHALL use the homepage when there is no separate listing.

#### Scenario: Navigation link to the calendar
- **WHEN** the homepage's navigation links "Calendar" to /calendar and the body links an individual show
- **THEN** /calendar is chosen as the events page

#### Scenario: Private events link
- **WHEN** the only events-like link is "Private Events" or a rentals page
- **THEN** it is not chosen

#### Scenario: Homepage lists the shows
- **WHEN** the only events-like links point to individual event pages
- **THEN** no separate events page is chosen and the homepage is used

### Requirement: The report records the page that actually loaded
When the sheet's URL returns 404 or 410, the check SHALL fall back to the site's homepage. The report SHALL record the final URL that loaded, after redirects.

#### Scenario: Moved events page
- **WHEN** the sheet's URL `https://example.com/old-events` returns 404 and the homepage loads
- **THEN** the venue is checked from the homepage and the report's url is the homepage

### Requirement: Pages needing JavaScript are flagged
The check SHALL flag a venue as JavaScript-heavy when none of its fetched pages has at least 500 characters of text without JavaScript.

#### Scenario: Script-rendered site
- **WHEN** a venue's pages have under 500 characters of visible text
- **THEN** the venue is flagged js_heavy in the report

### Requirement: The check identifies itself honestly and can be scoped
The check SHALL send the user agent `Mozilla/5.0 (compatible; venue-db-event-check/1.0)`. It SHALL skip inactive venues unless asked to include them, and SHALL accept a state filter and a limit.

#### Scenario: State filter
- **WHEN** the check runs with `--state NH`
- **THEN** only active New Hampshire venues are in the report
