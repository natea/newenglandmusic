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

When `fetch_events` runs, a venue with a SeatGeek venue ID, and no Ticketmaster or Eventbrite link, SHALL get its upcoming concerts from the SeatGeek API. The SeatGeek API SHALL replace the venue's ticketing-page and AI sources, but not its iCal feed or JSON-LD. Events SHALL be saved unapproved, matched on an external ID made from the SeatGeek event ID, and labelled by kind. Events that aren't music, such as sports, theater and comedy, SHALL be left out, and the report SHALL say how many.

#### Scenario: Concerts only

- **WHEN** a SeatGeek venue has five upcoming events: three concerts, one comedy show and one sports event
- **THEN** the three concerts are imported, and the report says two were left out

### Requirement: Only one API source per venue

A venue linked to more than one events API SHALL be fetched from exactly one, in this order: Ticketmaster, Eventbrite, SeatGeek.

#### Scenario: Linked to Ticketmaster and SeatGeek

- **WHEN** a venue has both a Ticketmaster and a SeatGeek link
- **THEN** it is fetched from Ticketmaster only

### Requirement: SeatGeek needs a client ID and fails gracefully

Without `SEATGEEK_CLIENT_ID`, linked venues SHALL be skipped with a note. An API error for one venue SHALL be reported as that venue's problem, and the run SHALL continue.

#### Scenario: API error

- **WHEN** the SeatGeek API returns an error for one venue
- **THEN** that venue is listed with a "seatgeek failed" problem, and the other venues are fetched
