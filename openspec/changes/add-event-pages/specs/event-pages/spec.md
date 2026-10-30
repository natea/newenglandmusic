## Purpose

Gives every approved event a page of its own on the site, where its acts, venue facts and outbound links sit together, so a listing can carry one link with one meaning.

## ADDED Requirements

### Requirement: Every approved event has a page
Each approved event SHALL have a page at `/event/<id>`, with or without performers. An unapproved or unknown event SHALL answer 404. The page SHALL replace the redirect into the calendar that the address used to answer, so the share link, calendar feeds and band pages that point at it open the page. A past event SHALL keep its page, marked as past.

#### Scenario: An approved event
- **WHEN** a visitor opens `/event/<id>` for an approved upcoming event
- **THEN** the site answers with the event's page, not a redirect

#### Scenario: An event with no performers
- **WHEN** a visitor opens the page of an approved event that has no linked artists or bands
- **THEN** the site answers with its page, showing the names from its title and artists as plain text

#### Scenario: Unapproved or unknown
- **WHEN** a visitor opens `/event/<id>` for an unapproved event, or an id that doesn't exist
- **THEN** the site answers 404

#### Scenario: A past event
- **WHEN** a visitor opens the page of an approved event that has already happened
- **THEN** the page shows the event and says it has passed

### Requirement: What the page shows
The page SHALL show, each only when the event has it: the date and start time; the show's own title, when it says something the act names don't; the headliner; the openers; the venue with its town, the age policy and the venue's accessibility notes (or the venue override in place of the venue); the price; the description; the action icons (calendar file, Google Calendar, map, share, save) as on the calendar; and the play buttons. A cancelled event SHALL say it is cancelled. Nothing the event lacks SHALL be drawn as an empty field.

#### Scenario: A full event
- **WHEN** a visitor opens the page of an event with a title, artists, a venue with a town and accessibility notes, a price, a description and play buttons
- **THEN** the page shows its date and time, title, headliner and openers, venue and town, the notes, the price, the description, the icon row and the play buttons

#### Scenario: A cancelled event
- **WHEN** a visitor opens the page of a cancelled event
- **THEN** the page says the event is cancelled

### Requirement: Acts link to their pages
On the event page, the headliner and each opener that is one of the event's performers SHALL link to its band or artist page. Names that aren't performers SHALL stay plain text. The headliner SHALL come first and stand out from the openers.

#### Scenario: Performers and a plain name
- **WHEN** an event's acts are Axe Collector, Phantom Rider and Anthropocene, and the first two are performers
- **THEN** the page links "Axe Collector" to `/bands/axe-collector` and "Phantom Rider" to its page, and "Anthropocene" stays plain

### Requirement: Tickets and the venue's page are separate, labelled links
The page SHALL show the ticket link as "Tickets" and the event's own link (usually the venue's page for the show) as "Venue's page", each opening in a new tab and marked as leaving the site. When both are the same URL, the page SHALL show one link, labelled "Tickets". When the event has only one of them, the page SHALL show only that one.

#### Scenario: Two different links
- **WHEN** an event's ticket link and event link differ
- **THEN** the page shows a "Tickets" link and a "Venue's page" link, to each

#### Scenario: The same link twice
- **WHEN** an event's ticket link and event link are the same URL
- **THEN** the page shows one "Tickets" link

#### Scenario: No ticket link
- **WHEN** an event has an event link and no ticket link
- **THEN** the page shows only the "Venue's page" link

### Requirement: The page shares well and stays out of search while unshared
The page SHALL have a title and description naming the event's acts, date and venue, and SHALL keep the preview metadata that shared links already show. While the site is unshared, the page SHALL tell search engines not to index it.

#### Scenario: Share preview
- **WHEN** a link to an event page is shared
- **THEN** its preview names the date, venue and acts, as the old redirect page's did

#### Scenario: Not indexed
- **WHEN** a search engine fetches an event page
- **THEN** the page asks not to be indexed

### Requirement: The page reads well on phones and to every visitor
The page SHALL fit a 390px-wide screen with no sideways scrolling, with the date, the headliner and the venue in the first screen; its links SHALL have names that say where they go; and its colours SHALL meet the site's contrast.

#### Scenario: On a phone
- **WHEN** the page is opened 390px wide
- **THEN** the date, headliner and venue are in the first screen, and nothing scrolls sideways
