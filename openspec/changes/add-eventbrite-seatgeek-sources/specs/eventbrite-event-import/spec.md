## Purpose

Import a venue's events from the official Eventbrite API, through the venue's Eventbrite organizer, for venues whose Eventbrite pages can't be crawled reliably.

## ADDED Requirements

### Requirement: Venues can be linked to an Eventbrite organizer

A venue SHALL be able to store an Eventbrite organizer ID, which admins can set, change and clear. The sheet sync SHALL NOT change it.

#### Scenario: Admin sets the organizer

- **WHEN** an admin enters an organizer ID on a venue's admin page and saves
- **THEN** the venue keeps that ID, and a later sheet sync leaves it unchanged

### Requirement: Organizers are found from the venue's own Eventbrite links

The organizer matching command SHALL read the Eventbrite event links on a venue's site and events page. It SHALL look up those events' organizers through the Eventbrite API, and SHALL link the venue when every event it found has the same organizer. When the events name more than one organizer, the venue SHALL NOT be linked and the report SHALL list the organizers. Venues that are already linked SHALL be skipped unless a re-check is asked for. A dry run SHALL save nothing.

#### Scenario: One organizer

- **WHEN** a venue's events page links three Eventbrite events, all by the same organizer
- **THEN** the venue is linked to that organizer

#### Scenario: Several organizers

- **WHEN** a venue's page links events by two different organizers
- **THEN** the venue is not linked, and the report lists both organizers with their names

### Requirement: Linked venues are fetched from the Eventbrite API

When `fetch_events` runs, a venue with an Eventbrite organizer ID and no Ticketmaster link SHALL get its events from the organizer's live events, keeping only those whose venue matches this venue by name or within 1 km. The Eventbrite API SHALL replace the venue's ticketing-page and AI sources, but not its iCal feed or JSON-LD. Imported events SHALL be saved unapproved, matched on an external ID made from the Eventbrite event ID, and labelled by kind like other imports.

#### Scenario: Organizer with events elsewhere

- **WHEN** an organizer has four live events, three at this venue and one in another town
- **THEN** only the three at this venue are imported

#### Scenario: Re-fetch updates instead of duplicating

- **WHEN** the same Eventbrite event is fetched again with a new start time
- **THEN** the existing event is updated, and no second event is created

### Requirement: Eventbrite needs a token and fails gracefully

Without `EVENTBRITE_API_KEY`, linked venues SHALL be skipped with a note. An API error for one venue SHALL be reported as that venue's problem, and the run SHALL continue.

#### Scenario: API error

- **WHEN** the Eventbrite API returns an error for one organizer
- **THEN** that venue is listed with an "eventbrite failed" problem, and the other venues are fetched
