## MODIFIED Requirements

### Requirement: The weekly job runs the source check and matching in order
The weekly job SHALL run, in this order: `check_event_sources`, `match_ticketmaster_venues`, `match_eventbrite_organizers`, `match_seatgeek_venues` and `lookup_venue_neighborhoods`.

#### Scenario: Weekly run
- **WHEN** the weekly job runs and every step succeeds
- **THEN** the five commands run in that order, and the job succeeds
