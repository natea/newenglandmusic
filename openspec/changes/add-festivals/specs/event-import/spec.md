## ADDED Requirements

### Requirement: Imported shows are matched to festivals
A show created or updated by `fetch_events` SHALL go through festival matching when it is saved, as any saved show does, and a re-fetch SHALL NOT change a festival an editor set or removed on it.

#### Scenario: New fetched show
- **WHEN** `fetch_events` saves a new unapproved show inside a festival's dates matching its title
- **THEN** the show is recorded with that festival as set automatically, though it isn't shown until approved

#### Scenario: Re-fetch keeps the editor's choice
- **WHEN** an editor marked an imported show as not part of any festival and `fetch_events` fetches it again
- **THEN** it still has no festival
