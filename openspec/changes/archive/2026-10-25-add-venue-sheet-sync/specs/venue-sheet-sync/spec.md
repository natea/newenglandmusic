# Spec Delta

## Purpose

Keeps the venue table in step with the "Northeastern US Music Venues" Google Sheet, which is the source of truth for venue details, matching rows to venues by a stable Venue_ID.

## ADDED Requirements

### Requirement: Venues are matched by Venue_ID
The sync SHALL match each sheet row to a venue by its `Venue_ID` and SHALL create a venue for an ID it hasn't seen and update the venue for an ID it has. Venue names SHALL NOT be used for matching.

#### Scenario: New row
- **WHEN** the sheet has a row whose Venue_ID is not in the database
- **THEN** a venue is created with that Venue_ID and the row's details

#### Scenario: Edited row
- **WHEN** a row's name or details change in the sheet and the sync runs
- **THEN** the venue with that Venue_ID is updated and no new venue is created

#### Scenario: Two venues with the same name
- **WHEN** two rows share a name, city and state but have different Venue_IDs
- **THEN** they are kept as two separate venues

### Requirement: The sheet must have usable Venue_IDs
The sync SHALL stop with an error and save nothing when the sheet has no `Venue_ID` column or a Venue_ID is used by more than one row. Rows with a name but no Venue_ID SHALL be skipped with a warning.

#### Scenario: Missing column
- **WHEN** the sheet has no Venue_ID column
- **THEN** the sync fails with an error saying so and no venue changes

#### Scenario: Duplicate Venue_ID
- **WHEN** two rows have the same Venue_ID
- **THEN** the sync fails naming the row and the ID, and no venue changes

#### Scenario: Row without an ID
- **WHEN** a row has a venue name but an empty Venue_ID
- **THEN** that row is skipped with a warning and the other rows are synced

### Requirement: Venues are never deleted by a sync
The sync SHALL NOT delete venues. Venues in the database whose Venue_ID is not in the sheet SHALL be reported and left unchanged.

#### Scenario: Row removed from the sheet
- **WHEN** a venue's row is deleted from the sheet and the sync runs
- **THEN** the venue stays in the database and the sync lists it as not in the sheet

### Requirement: Sheet values are normalized
The sync SHALL map Y/Yes and N/No to true and false and any other value to unknown, parse coordinates as numbers, map sizes like "Small (<100)" to a size choice, split semicolon-separated genres into a list, and map booking-type labels to known choices.

#### Scenario: Uncertain yes/no value
- **WHEN** a yes/no column holds "Maybe?" or is blank
- **THEN** the venue's field is saved as unknown, not as false

#### Scenario: Genre list
- **WHEN** the genre column holds "Funk; Jazz;"
- **THEN** the venue's genres are ["Funk", "Jazz"]

#### Scenario: Unknown booking type
- **WHEN** a row's booking type isn't one of the known labels
- **THEN** the venue's booking type is left blank and the sync prints a warning naming the row

### Requirement: A sync is all or nothing and can be previewed
The sync SHALL apply all row changes in one transaction. With `--dry-run` it SHALL report how many venues it would create and update, and save nothing.

#### Scenario: Dry run
- **WHEN** the sync runs with `--dry-run`
- **THEN** it reports the created and updated counts and the database is unchanged

### Requirement: Fields not in the sheet are preserved
The sync SHALL only write fields that come from sheet columns. Other venue fields SHALL keep their values.

#### Scenario: Database-only field
- **WHEN** a venue has a value in a field that no sheet column maps to and the sync runs
- **THEN** that value is unchanged

### Requirement: Inactive venues are hidden from venue pickers
Venues the sheet marks inactive SHALL NOT be offered in venue search or the event submission form, and pickers SHALL label venues with their city and state.

#### Scenario: Searching for a closed venue
- **WHEN** a user searches venues by the name of a venue marked inactive
- **THEN** it does not appear in the results
