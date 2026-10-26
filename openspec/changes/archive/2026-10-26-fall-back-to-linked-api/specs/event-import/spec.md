## ADDED Requirements

### Requirement: A failed feed falls back to the venue's linked API
When a venue's iCal feed or JSON-LD fetch fails and yields no events, and the venue is linked to Ticketmaster or to an Eventbrite organizer that the run isn't skipping, the import SHALL fetch the venue's events from that API in the same run: Ticketmaster first, then Eventbrite. The events SHALL be saved, and the venue's fetch status recorded, as from that API, and the venue SHALL NOT also be sent to AI extraction. A venue whose saved source yields events SHALL NOT be fetched from the API.

#### Scenario: JSON-LD blocked, linked to Eventbrite
- **WHEN** a venue's JSON-LD pages return HTTP 403 and the venue is linked to an Eventbrite organizer
- **THEN** its events are fetched from Eventbrite in the same run and saved with the `eventbrite` source

#### Scenario: Saved source works
- **WHEN** a linked venue's JSON-LD yields events
- **THEN** no API request is made for it

#### Scenario: Unparseable iCal feed, linked to Eventbrite
- **WHEN** a venue's iCal feed can't be parsed and the venue is linked to an Eventbrite organizer
- **THEN** its events come from Eventbrite, and its events page isn't sent to AI extraction

#### Scenario: Not linked
- **WHEN** a venue's JSON-LD fetch fails and it has no API link
- **THEN** it is reported as failing, as before

#### Scenario: API skipped
- **WHEN** the fetch runs with `--skip-eventbrite` and an Eventbrite-linked venue's JSON-LD fails
- **THEN** no Eventbrite request is made for it, and it is reported as failing

### Requirement: A fallback that works isn't reported as a failure
When the fallback gets the venue's events, the saved source's failure SHALL be reported as a note saying which API was used instead, and SHALL NOT count as a problem on the job run or in the venue's fetch status. When the API fetch fails too, both failures SHALL be reported as problems.

#### Scenario: Fallback works
- **WHEN** a venue's JSON-LD fails and its Eventbrite fallback returns events
- **THEN** the report notes that JSON-LD failed and Eventbrite was used, and the venue has no problems on the job run or in its fetch status

#### Scenario: Fallback fails too
- **WHEN** a venue's JSON-LD fails and its Eventbrite request returns an error
- **THEN** both the JSON-LD failure and the Eventbrite failure are listed as the venue's problems
