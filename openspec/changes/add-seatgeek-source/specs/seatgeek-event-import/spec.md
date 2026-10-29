## Purpose

Import a venue's events from the official SeatGeek API, for venues whose ticketing pages (AXS, Etix, Eventim and others) refuse our crawler and that Ticketmaster doesn't list.

## ADDED Requirements

### Requirement: Venues can be linked to a SeatGeek venue

A venue SHALL be able to store a SeatGeek venue ID, which admins can set, change and clear. The sheet sync SHALL NOT change it.

#### Scenario: Admin sets the SeatGeek venue

- **WHEN** an admin enters a SeatGeek venue ID on a venue's admin page and saves
- **THEN** the venue keeps that ID, and a later sheet sync leaves it unchanged

### Requirement: SeatGeek venues are matched by name and distance

The SeatGeek matching command SHALL search SeatGeek venues by each venue's name and state. It SHALL consider only results with a matching name within 1 km of the venue's location, preferring ones with upcoming events. It SHALL link the one whose name is the same as the venue's when exactly one is; otherwise the only candidate, when there is just one. A dry run SHALL save nothing.

#### Scenario: One clear match

- **WHEN** one SeatGeek venue in the same state has a matching name and is within 1 km of the venue
- **THEN** the venue is linked to it

### Requirement: Uncertain SeatGeek matches are reported

A venue the SeatGeek matching command can't link with certainty SHALL be left unlinked. The report SHALL list it with each candidate's ID, name, address, distance and upcoming event count, so an admin can set the ID by hand.

#### Scenario: Ambiguous

- **WHEN** two SeatGeek venues within 1 km both merely contain the venue's name, and both have upcoming events
- **THEN** the venue is not linked, and the report lists both candidates

### Requirement: Linked venues are fetched from the SeatGeek API

When `fetch_events` runs, a venue with a SeatGeek venue ID, and no Ticketmaster or Eventbrite link, SHALL get its upcoming concerts from the SeatGeek API. The SeatGeek API SHALL replace the venue's ticketing-page and AI sources, but not its iCal feed. It SHALL replace the venue's JSON-LD only in a run where SeatGeek has more upcoming concerts than the JSON-LD found upcoming events, and the report SHALL give both counts. Events SHALL be saved unapproved, matched on an external ID made from the SeatGeek event ID, and labelled by kind. Events that aren't music, such as sports, theater and comedy, SHALL be left out, and the report SHALL say how many.

#### Scenario: Concerts only

- **WHEN** a SeatGeek venue has five upcoming events: three concerts, one comedy show and one sports event
- **THEN** the three concerts are imported, and the report says two were left out

### Requirement: SeatGeek events link to the venue's own seller

A venue SHALL be able to store a ticket page, which admins can set, change and clear, and which the sheet sync SHALL NOT change. A SeatGeek event SHALL store its SeatGeek page as its source URL, which the site SHALL NOT show. Its event link and ticket link SHALL be, in order: the show's own Etix or AXS page, when exactly one show link on the venue's own events page matches the event's title or headliner; else the venue's ticket page; else the venue's website; else empty. A SeatGeek event SHALL have no price.

When fetching a SeatGeek venue, its own events page SHALL be read once, obeying robots.txt, and so SHALL its homepage, and their links SHALL be combined. A venue with a blank ticket page SHALL get the one Etix or AXS venue link found there, if there's exactly one. A ticket page that's already set SHALL NOT be changed. A page that can't be read SHALL be noted, and SHALL NOT be counted as a problem.

#### Scenario: Show's own page found

- **WHEN** a SeatGeek event "As I Lay Dying" is imported for a venue whose events page links `https://www.etix.com/ticket/p/96934398/as-i-lay-dying-new-haven-toads-place-of-new-haven`
- **THEN** the event's link and ticket link are that Etix page

#### Scenario: Recurring title

- **WHEN** a SeatGeek event's title matches two different show links on the venue's events page
- **THEN** the event links to the venue's ticket page instead

#### Scenario: Venue's list found on its site

- **WHEN** a venue with a blank ticket page has an events page linking `https://www.etix.com/ticket/v/677`
- **THEN** its ticket page becomes that link, and its SeatGeek events with no show link of their own link there

#### Scenario: Ticket page already set

- **WHEN** a venue's ticket page is set, and its events page links a different Etix venue page
- **THEN** the ticket page is unchanged

#### Scenario: Venue's site can't be read

- **WHEN** the venue's events page fails, or robots.txt disallows it
- **THEN** the events are imported with the venue's ticket page or website as their link, and the run notes it without counting a problem

#### Scenario: Venue sells through Etix

- **WHEN** a SeatGeek event is imported for a venue whose ticket page is its Etix listing
- **THEN** the event's link and ticket link are that Etix page, its source URL is the SeatGeek page, and it has no price

#### Scenario: No ticket page

- **WHEN** a SeatGeek event is imported for a venue with a website but no ticket page
- **THEN** the event's link and ticket link are the venue's website

#### Scenario: SeatGeek link not shown

- **WHEN** an approved SeatGeek event is shown on the site
- **THEN** the page has no link to SeatGeek

#### Scenario: JSON-LD from a single show's page

- **WHEN** a SeatGeek-linked venue's JSON-LD finds 1 upcoming event, and SeatGeek has 14 concerts there
- **THEN** the 14 SeatGeek concerts are imported, the JSON-LD event isn't, and the report gives both counts

#### Scenario: JSON-LD lists more

- **WHEN** a SeatGeek-linked venue's JSON-LD finds 47 upcoming events, and SeatGeek has 22 concerts there
- **THEN** the 47 JSON-LD events are imported, and no SeatGeek events

#### Scenario: Show links on the homepage

- **WHEN** a venue's saved events page is a single show's page, linking only that show, and its homepage links each show's Etix page
- **THEN** its SeatGeek events link to the show pages found on the homepage

### Requirement: Only one API source per venue

A venue linked to more than one events API SHALL be fetched from exactly one, in this order: Ticketmaster, Eventbrite, SeatGeek.

#### Scenario: Linked to Ticketmaster and SeatGeek

- **WHEN** a venue has both a Ticketmaster and a SeatGeek link
- **THEN** it is fetched from Ticketmaster only

#### Scenario: Linked to Eventbrite and SeatGeek

- **WHEN** a venue has both an Eventbrite organizer and a SeatGeek link
- **THEN** it is fetched from Eventbrite only

### Requirement: SeatGeek needs a client ID and fails gracefully

Without `SEATGEEK_CLIENT_ID`, linked venues SHALL be skipped with a note. An API error for one venue SHALL be reported as that venue's problem, and the run SHALL continue.

#### Scenario: API error

- **WHEN** the SeatGeek API returns an error for one venue
- **THEN** that venue is listed with a "seatgeek failed" problem, and the other venues are fetched
