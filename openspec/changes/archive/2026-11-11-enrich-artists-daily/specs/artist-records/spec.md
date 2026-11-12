## ADDED Requirements

### Requirement: New artists and bands are looked up on MusicBrainz every day
The daily job SHALL look up on MusicBrainz at most 100 artists and bands per run, from those not yet looked up (bands first, then artists, each by name), and SHALL NOT refresh records looked up before. A lookup that finishes counts, whether matched, ambiguous or not found. A run MusicBrainz asks to wait SHALL stop and keep what it found, and the next day's run carries on.

#### Scenario: More records than the limit
- **WHEN** 130 records have not been looked up and the daily step runs with its limit of 100
- **THEN** 100 are looked up, bands before artists, and 30 remain for the next day

#### Scenario: A band's members
- **WHEN** a band not yet looked up is found on MusicBrainz and its members are not yet records
- **THEN** the members are added as artists not yet looked up, and a later daily run looks them up and fills in their bio, photo and links

#### Scenario: Already looked up
- **WHEN** the daily step runs and every record has been looked up before, whether matched, ambiguous or not found
- **THEN** no MusicBrainz request is made for any of them

#### Scenario: MusicBrainz asks to wait
- **WHEN** MusicBrainz asks the run to wait partway through the step
- **THEN** the run stops, the records already looked up keep what was found, and the rest are looked up on the next day's run

#### Scenario: Unmatched records are not retried
- **WHEN** a record was looked up and left ambiguous, and the daily step runs again
- **THEN** it is not looked up again, and an editor can still settle or clear it in the admin

#### Scenario: A record held for review
- **WHEN** a record held for review has not been looked up
- **THEN** the daily step looks it up, and it stays hidden from the public site until an editor marks it ready
