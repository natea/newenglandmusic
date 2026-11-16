## MODIFIED Requirements

### Requirement: An A–Z index of bands and artists
The site SHALL list every live band and artist at `/bands`, together, ordered by name ignoring a leading "The", grouped under their first letter (names starting with a digit or symbol under "#"), with a rail of the letters that have acts, each linking to its group. Each entry SHALL show the act's name linking to its page, whether it's a band or an artist, its home town and state when known, and the date of its next upcoming approved show when it has one. An act held for review SHALL NOT be listed, and neither SHALL an act marked inactive. `/artists` SHALL redirect to `/bands`, and the index's and act pages' addresses typed with a trailing slash, or in the singular (`/band`, `/artist/...`), SHALL redirect to their own address. The site's menu SHALL link to the index as "Bands & artists".

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
