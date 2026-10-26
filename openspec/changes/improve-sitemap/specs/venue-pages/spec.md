# Spec Delta

## Purpose

A public page for each active venue, so people can find a venue and its upcoming shows, and so the venue names in listings lead somewhere.

## ADDED Requirements

### Requirement: Each active venue has a page

Each active venue SHALL have a page at `/venue/<slug>/`. The page SHALL show:
- the venue's name, town and state;
- the venue's public details from the sheet: its type, size, genres, age policy, accessibility notes and website, where they are set;
- a link to the venue on Google Maps;
- its upcoming approved events, soonest first, rendered as they are in the listings.

It SHALL NOT show the venue's safety flag or notes, or its booking notes. A venue that isn't active SHALL return 404.

#### Scenario: Venue with upcoming shows

- **WHEN** a visitor opens the page of an active venue that has three upcoming approved events and one unapproved event
- **THEN** the page returns 200, shows the venue's name, town and state, and lists the three approved events, soonest first

#### Scenario: Venue with no upcoming shows

- **WHEN** a visitor opens the page of an active venue with no upcoming approved events
- **THEN** the page returns 200, shows the venue's details, and says there are no upcoming shows

#### Scenario: Inactive venue

- **WHEN** a visitor opens the page of a venue marked inactive
- **THEN** the response is 404

#### Scenario: Private fields stay private

- **WHEN** a visitor opens the page of a venue with safety notes and booking notes
- **THEN** neither appears on the page

### Requirement: Venue pages show only Places data we may keep

A venue page SHALL NOT display a venue's stored Google Places name, address, phone, website or business status. Its map link SHALL be built from the venue's place ID when one is matched, and from its name and town otherwise.

#### Scenario: Matched venue

- **WHEN** a visitor opens the page of a venue with a confident Places match
- **THEN** the map link opens Google Maps for that place ID, and the Places address and phone don't appear

### Requirement: A venue keeps its address

A venue's slug SHALL be made from its name and town when the venue is created, SHALL be unique, and SHALL NOT change when the venue is renamed, so links to it keep working.

#### Scenario: Two venues with the same name

- **WHEN** two active venues are both called "The Middle East", in different towns
- **THEN** each has its own page at a different address

#### Scenario: Renamed venue

- **WHEN** an admin renames a venue
- **THEN** its page stays at the same address

### Requirement: Listings link to venue pages

Wherever an event is listed, the venue's name SHALL link to the venue's page when the venue is active.

#### Scenario: Event in the home page listing

- **WHEN** a visitor views an event at an active venue in the home page listing
- **THEN** the venue's name links to `/venue/<slug>/`
