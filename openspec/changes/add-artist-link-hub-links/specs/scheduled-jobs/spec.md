## MODIFIED Requirements

### Requirement: The weekly job runs the source check and matching in order
The weekly job SHALL run, in this order: `check_event_sources`, `match_ticketmaster_venues`, `match_eventbrite_organizers`, `match_seatgeek_venues`, `lookup_venue_neighborhoods` and `read_artist_link_hubs`. The link-hub reading runs last, after the venue steps. A failure in it SHALL fail the run without stopping the other steps, as the other steps do, and it SHALL be recorded as a `JobRun` with a summary of the records read, filled, flagged and failed.

#### Scenario: Weekly run
- **WHEN** the weekly job runs and every step succeeds
- **THEN** the six commands run in that order, the job succeeds, and the hub step's summary is listed at `/admin/core/jobrun/`
