# Spec Delta

## MODIFIED Requirements

### Requirement: An A–Z index of bands and artists
The site SHALL list every live band and artist at `/bands`, together, ordered by name ignoring a leading "The", grouped under their first letter (names starting with a digit or symbol under "#"), with a rail of the letters that have acts, each linking to its group. Each entry SHALL show the act's name linking to its page, whether it's a band or an artist, its home town and state when known, and the date of its next upcoming approved show when it has one. An act held for review SHALL NOT be listed, and neither SHALL an act marked inactive. `/artists` SHALL redirect to `/bands`, and the index's and act pages' addresses typed with a trailing slash, or in the singular (`/band`, `/artist/...`), SHALL redirect to their own address. The site's header SHALL link to the index as "Bands", and the index's own heading and breadcrumb SHALL read "Bands & artists".

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

#### Scenario: Inactive acts left out
- **WHEN** the band "The Cars" and the artist "Greg Humphreys" are marked inactive
- **THEN** neither is on `/bands`, and the count of acts on the page leaves them out

#### Scenario: Inactive acts keep their pages and links
- **WHEN** "The Cars" is marked inactive and has an approved show
- **THEN** `/bands/the-cars` still opens, the show still links to it, and a search for "cars" still finds it

#### Scenario: Inactive and held are independent
- **WHEN** one act is inactive but not held for review, and another is held but not inactive
- **THEN** the inactive one's page still opens, and the held one is left off the index and has no page

#### Scenario: The artists address
- **WHEN** a visitor opens `/artists`
- **THEN** they're redirected to `/bands`

#### Scenario: A trailing slash
- **WHEN** a visitor opens `/bands/` or `/bands/belly/`
- **THEN** they're redirected to `/bands` or `/bands/belly`

#### Scenario: The singular
- **WHEN** a visitor opens `/band` or `/artist/anjimile/`
- **THEN** they're redirected to `/bands` or `/artists/anjimile`

#### Scenario: The header's link
- **WHEN** a visitor follows "Bands" in the header
- **THEN** `/bands` opens, headed "Bands & artists"

### Requirement: The search box is at the top of every page
The search box SHALL be in the header of every page, beside the site's name, not behind a menu. On the search results page it SHALL hold what was searched, and the page SHALL have no other search box.

#### Scenario: On every page
- **WHEN** a visitor opens any page
- **THEN** the search box is in view in the header, without opening a menu

#### Scenario: One box on the results page
- **WHEN** a visitor searches for "belly"
- **THEN** the results page has one search box, holding "belly", and it suggests as the others do

## REMOVED Requirements

### Requirement: The index is set like a book's index
**Reason**: The new design sets each letter as one run of entries under a single guide line, and prints names as they are; 40-entry pages and the inverted "The" belonged to the book-index look.
**Migration**: None for visitors. "Each letter opens with a guide line" below takes its place; acts are still filed ignoring a leading "The".

## ADDED Requirements

### Requirement: Each letter opens with a guide line
Each letter SHALL open with its large initial, the number of acts under it, and one guide line naming its first and last acts ("184 acts · Bark At The Moon to Byrne Bros"), over its entries in two columns at 1024px wide and up and one column below. A name starting "The" SHALL be filed ignoring it and printed as the act's own name ("The Blue Stones", under B).

#### Scenario: A letter's guide line
- **WHEN** the letter B has 184 acts, the first "Bark At The Moon" and the last "Byrne Bros"
- **THEN** B's section opens with "B", "184 acts" and "Bark At The Moon to Byrne Bros", once

#### Scenario: "The" names filed without it, printed with it
- **WHEN** the site has "The Atlantics"
- **THEN** the index lists it under A, printed "The Atlantics", and its page and a search for it print "The Atlantics"
