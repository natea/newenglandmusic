## MODIFIED Requirements

### Requirement: The weekly job runs the source check and matching in order
The weekly job SHALL run, in this order, the commands `check_event_sources`, `match_ticketmaster_venues`, `match_eventbrite_organizers`, `match_seatgeek_venues`, `lookup_venue_neighborhoods`, `read_artist_link_hubs` and `find_bandcamp_embeds`. `read_artist_link_hubs` is added by `add-artist-link-hub-links`, which must be archived first. The Bandcamp step runs last, so a Bandcamp link a link hub just filled is looked up in the same run. A failure in it SHALL fail the run without stopping an earlier step, and it SHALL be recorded as a `JobRun` listed at `/admin/core/jobrun/`.

#### Scenario: Weekly run
- **WHEN** the weekly job runs and every step succeeds
- **THEN** the seven commands run in that order, the job succeeds, and the Bandcamp step's summary (looked up, found, no playable release, failed) is listed at `/admin/core/jobrun/`

#### Scenario: Bandcamp step fails
- **WHEN** `find_bandcamp_embeds` fails
- **THEN** the earlier steps have run, the job is marked failed, and the failure is recorded
