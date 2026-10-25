## MODIFIED Requirements

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
