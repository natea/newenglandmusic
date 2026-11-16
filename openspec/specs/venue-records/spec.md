# venue-records Specification

## Purpose

Keeps the site's venues in the admin, now that the venue sheet no longer syncs into them: editors change a venue's details there, and add new venues there, each with a venue ID like the ones the sheet gave.

## Requirements

### Requirement: Venues are kept in the admin
Editors SHALL be able to change every venue field the sheet used to set, and to add venues, in the admin. Nothing on a schedule SHALL overwrite an editor's change to a venue's details.

#### Scenario: An edit stays
- **WHEN** an editor changes a venue's town in the admin and the daily job runs
- **THEN** the venue keeps the editor's town

### Requirement: A new venue gets the next venue ID
A venue added in the admin without a venue ID SHALL be given the next one in the sheet's form: "V" and the number one higher than the highest existing venue ID's, zero-padded to the same width ("V0731" after "V0730"). An ID an editor types SHALL be kept, and SHALL be refused if another venue has it.

#### Scenario: The next ID
- **WHEN** the highest venue ID is "V0730" and an editor adds a venue leaving the ID empty
- **THEN** the new venue's ID is "V0731"

#### Scenario: A duplicate ID
- **WHEN** an editor adds a venue with the ID another venue already has
- **THEN** the admin refuses it, saying the ID is taken
