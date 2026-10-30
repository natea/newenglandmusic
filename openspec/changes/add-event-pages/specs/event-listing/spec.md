## Purpose

Defines how one event's row reads in the calendar, the Saved shows page and search results: one link per row, to the event's own page, with the headliner set above the openers.

## ADDED Requirements

### Requirement: The headline links to the event page
Each listed event SHALL have one headline link, to its own page at `/event/<id>`, opening in the same tab. No other text in the row's description of the show (the title line, act names, venue) SHALL be a link. The ticket badge, the icon row and the play buttons SHALL keep their own links. The row SHALL carry no separate "info" link.

#### Scenario: One link to the event page
- **WHEN** an event with performers is listed
- **THEN** its headline links to `/event/<id>`, its act names and venue are plain text, and it has no "info" link

#### Scenario: An event with no performers
- **WHEN** an event without performers is listed
- **THEN** its headline also links to `/event/<id>`, not to the venue's site

### Requirement: Headliner first, openers after "with"
The listing SHALL name the event's acts in billing order: the first act (the headliner) in bold and a step larger than the row's text, then the other acts in regular weight after "with", separated by commas. Acts SHALL be taken from the event's title and artists as the artist names are read (`event-artist-names`). An event whose title names no act (a kind of night, such as "Jazz Jam") SHALL show its title as the headline instead.

#### Scenario: A headliner and openers
- **WHEN** an event titled "Disko Lunatics" has the artists "Miss Chief, Trading Tombstones"
- **THEN** the row shows "Disko Lunatics" bold and larger, then "with Miss Chief, Trading Tombstones" in regular weight

#### Scenario: No act in the title
- **WHEN** an event is titled "Bluegrass Jam" and has the artists "Frank Drake"
- **THEN** the headline is "Frank Drake"; and an event titled "Bluegrass Jam" with no artists has "Bluegrass Jam" as its headline

### Requirement: The show's title as a line of its own
When the event's title says something its act names don't, such as an occasion or a tour ("Halloween Show", "20 Years of Nekrogoblikon with Special Guests"), the row SHALL show the title as a small, quiet line above the headline. When the title is only the act names, it SHALL NOT be shown again.

#### Scenario: A title that adds something
- **WHEN** an event is titled "Halloween Show" and its artists are "Disko Lunatics, Miss Chief"
- **THEN** "Halloween Show" is a small line above the headline "Disko Lunatics"

#### Scenario: A title that is only the names
- **WHEN** an event is titled "Dev Lemons, Venus & the Flytraps" and its artists are "Dev Lemons, Venus & the Flytraps"
- **THEN** the row shows "Dev Lemons" with "Venus & the Flytraps" once, and no title line

### Requirement: Each act is named once
An act named by both the title and the artists SHALL appear once in the row, in the position the title gives it.

#### Scenario: The headliner in both
- **WHEN** an event titled "Kim Deal" has the artists "Kim Deal, Pile"
- **THEN** the row shows "Kim Deal" as the headline and "with Pile", and "Kim Deal" once

### Requirement: The ticket badge stays
An event with a ticket link SHALL keep the "tix" badge at the right of its row, linking straight to the ticket page in a new tab.

#### Scenario: Ticket badge
- **WHEN** an event with a ticket link is listed
- **THEN** the row shows the "tix" badge linking to that ticket page
