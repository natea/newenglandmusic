## MODIFIED Requirements

### Requirement: Imported events are queued for review without duplicates
Each event SHALL get an external ID from its source. A new event SHALL be saved unapproved. An event with an existing external ID SHALL be updated in place, keeping its approval. An event with a new external ID SHALL instead update an existing imported event at the same venue with the same start time and the same title, ignoring case, spaces and punctuation, keeping its approval and kind, and taking the new external ID. Events entered by hand SHALL NOT be updated this way.

#### Scenario: Re-running the import
- **WHEN** the import runs twice over the same feed
- **THEN** no duplicates are created and the second run reports the events as updated

#### Scenario: Previously approved event
- **WHEN** an approved event is re-imported with a changed description
- **THEN** its description changes and it stays approved

#### Scenario: Same show under a new ID
- **WHEN** a venue's approved scraped event "Gryme" at 9 pm on Oct 30 exists, and the Eventbrite import brings "GRYME" at the same time under an Eventbrite ID
- **THEN** the existing event is updated and takes the Eventbrite ID, stays approved and keeps its kind, and no second event is created

#### Scenario: Hand-entered event
- **WHEN** an event entered by hand has the same venue, start time and title as an imported one
- **THEN** the imported event is saved separately, and the hand-entered event is unchanged

## ADDED Requirements

### Requirement: Existing duplicates can be merged
The `dedupe_events` command SHALL find upcoming imported events that share a venue, start time and normalised title. In each group it SHALL keep the oldest copy whose source is the venue's latest fetch source, or the oldest copy when none is. The kept copy SHALL be approved if any copy was, and SHALL take an admin-set kind from another copy when it has none of its own. The other copies SHALL be deleted. With `--dry-run` it SHALL list each group's kept and deleted copies and change nothing.

#### Scenario: Eventbrite and scraped copies
- **WHEN** a venue last fetched from Eventbrite has an approved scraped copy and an unapproved Eventbrite copy of the same show
- **THEN** the Eventbrite copy is kept and approved, and the scraped copy is deleted

#### Scenario: Equal copies
- **WHEN** two AI copies of a show exist and neither is from the venue's latest fetch source
- **THEN** the older one is kept

#### Scenario: Admin label carried over
- **WHEN** the copy to delete has a kind an admin set, and the kept copy's kind came from AI
- **THEN** the kept copy takes the admin's kind

#### Scenario: Dry run
- **WHEN** the command runs with `--dry-run`
- **THEN** it lists every group with the copy it would keep and those it would delete, and no event changes
