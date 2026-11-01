## Purpose

Lets visitors find any band or artist on the site, with or without an upcoming show: an A–Z index of every live act, and acts in the site's search.

## ADDED Requirements

### Requirement: An A–Z index of bands and artists
The site SHALL list every live band and artist at `/bands`, together, ordered by name ignoring a leading "The", grouped under their first letter (names starting with a digit or symbol under "#"), with a rail of the letters that have acts, each linking to its group. Each entry SHALL show the act's name linking to its page, whether it's a band or an artist, its home town and state when known, and the date of its next upcoming approved show when it has one. An act held for review SHALL NOT be listed. `/artists` SHALL redirect to `/bands`. The site's menu SHALL link to the index as "Bands & artists".

#### Scenario: Bands and artists together
- **WHEN** the site has the band "Belly" from Providence, RI and the artist "Anjimile" from Boston, MA
- **THEN** `/bands` lists Anjimile under A and Belly under B, each linking to its page, with its kind and town

#### Scenario: A leading "The" and digits
- **WHEN** the site has "The Atlantics" and "28 Degrees Taurus"
- **THEN** The Atlantics is listed under A, and 28 Degrees Taurus under #

#### Scenario: The next show
- **WHEN** Belly has an approved show on Nov 14 and Anjimile has none
- **THEN** Belly's entry shows Nov 14, and Anjimile's shows no date

#### Scenario: Held acts left out
- **WHEN** the band "3 1/2 Girls" is held for review
- **THEN** it isn't on the index

#### Scenario: The artists address
- **WHEN** a visitor opens `/artists`
- **THEN** they're redirected to `/bands`

### Requirement: Search finds bands and artists
A search SHALL list the live bands and artists whose names contain the search words (ignoring case and accents), above the shows and pages it finds, each with its name linking to its page, its kind and its town. Acts held for review SHALL NOT be listed. A search that finds no act SHALL show no acts section.

#### Scenario: A band by name
- **WHEN** a visitor searches for "belly"
- **THEN** the results list the band Belly, linking to `/bands/belly`, above any shows that match

#### Scenario: No act matches
- **WHEN** a visitor searches for "karaoke"
- **THEN** the results show shows and pages only, with no acts section

### Requirement: The index reads well on phones
The index SHALL fit a 390px-wide screen with no sideways scrolling, its letter rail wrapping onto as many lines as it needs.

#### Scenario: On a phone
- **WHEN** `/bands` is opened 390px wide
- **THEN** the letter rail and the entries fit the width, and nothing scrolls sideways
