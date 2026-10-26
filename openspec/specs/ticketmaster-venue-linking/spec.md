# ticketmaster-venue-linking Specification

## Purpose
Links each venue in the database to its Ticketmaster venue, so its events can be fetched from the Ticketmaster Discovery API, while making sure a wrong match never silently attaches another venue's events.

## Requirements

### Requirement: Venues can store a Ticketmaster venue link
Each venue SHALL be able to hold at most one Ticketmaster venue ID. The link SHALL be optional, editable in the admin, and SHALL NOT be changed or cleared by syncing venues from the Google Sheet.

#### Scenario: Admin links a venue by hand
- **WHEN** an admin enters a Ticketmaster venue ID on a venue in the admin and saves
- **THEN** the venue keeps that ID and later event fetches use it

#### Scenario: Sheet sync leaves the link alone
- **WHEN** a venue with a Ticketmaster venue ID is re-synced from the Google Sheet
- **THEN** its Ticketmaster venue ID is unchanged

### Requirement: Matching links only confident matches
The matching command SHALL search Ticketmaster venues by each venue's name and state. It SHALL consider only candidates with a matching name within 1 km of the venue's location (its confident looked-up coordinates, else its sheet coordinates). When any of those candidates has upcoming events, it SHALL consider only the ones that do. It SHALL link the one whose name is the same as the venue's when exactly one is; otherwise the only candidate, when there is just one.

#### Scenario: One clear match
- **WHEN** a single Ticketmaster venue in the same state has a matching name and is within 1 km of the venue
- **THEN** the venue is linked to that Ticketmaster venue ID

#### Scenario: Duplicate listing without coordinates
- **WHEN** Ticketmaster lists the venue twice, once with coordinates within 1 km and once without coordinates
- **THEN** the venue is linked to the listing within 1 km

#### Scenario: Same name preferred over a longer one
- **WHEN** "Big Night Live" and "PLAY Boston at Big Night Live" both lie within 1 km of Big Night Live
- **THEN** the venue is linked to "Big Night Live"

#### Scenario: Listing with events preferred
- **WHEN** "Off The Rails" (no upcoming events) and "Off The Rails Music Venue" (14 upcoming events) both lie within 1 km of Off The Rails
- **THEN** the venue is linked to "Off The Rails Music Venue"

#### Scenario: Ambiguous or distant candidates
- **WHEN** several candidates within 1 km have the venue's exact name, or none does and several merely contain it, or no name match lies within 1 km, or the venue has no coordinates
- **THEN** the venue is not linked and the report lists it with its candidates' IDs, names, addresses, distances and upcoming event counts

#### Scenario: No candidates
- **WHEN** the search returns no Ticketmaster venues
- **THEN** the venue is not linked and the report lists it as unmatched

### Requirement: Matching never overwrites existing links
The matching command SHALL skip venues that already have a Ticketmaster venue ID unless explicitly told to re-check them. It SHALL support a dry run that reports matches without saving.

#### Scenario: Previously linked venue
- **WHEN** the matching command runs over a venue that already has a Ticketmaster venue ID
- **THEN** the existing link is kept and the venue is reported as already linked

#### Scenario: Dry run
- **WHEN** the matching command runs in dry-run mode
- **THEN** it reports what it would link and saves nothing

### Requirement: Matching can be limited to chosen venues
The matching command SHALL by default check active venues whose saved event-source result lists Ticketmaster or Live Nation among its ticketing platforms. It SHALL accept a list of venue sheet IDs, or an option to check every active venue. With no venue options and no saved results, it SHALL fail with an error telling the user to run the source check first, or to pass sheet IDs or the option to check every venue.

#### Scenario: Default selection
- **WHEN** the matching command runs with no venue options
- **THEN** it checks only active venues whose event-source report names Ticketmaster or Live Nation

#### Scenario: Explicit venues
- **WHEN** the matching command is given sheet IDs
- **THEN** it checks only those venues

#### Scenario: No saved results
- **WHEN** the matching command runs with no venue options and no event-source results have been saved
- **THEN** it exits with an error telling the user to run the source check first, or to pass `--sheet-ids` or `--all`

### Requirement: Matching needs an API key
The matching command SHALL stop with a clear error when no Ticketmaster API key is configured.

#### Scenario: Missing key
- **WHEN** the matching command runs without `TICKETMASTER_API_KEY` set
- **THEN** it exits with an error naming the missing setting and links nothing
