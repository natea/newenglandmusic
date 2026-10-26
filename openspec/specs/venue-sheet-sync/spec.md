# venue-sheet-sync Specification

## Purpose
Keeps the venue table in step with the "Northeastern US Music Venues" Google Sheet, which is the source of truth for venue details, matching rows to venues by a stable Venue_ID.

## Requirements

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
The sync SHALL apply all venue and area changes in one transaction. With `--dry-run` it SHALL report how many venues it would create and update, and how many areas it would add, update and remove, and save nothing.

#### Scenario: Dry run
- **WHEN** the sync runs with `--dry-run`
- **THEN** it reports the venue counts (created, updated) and the area counts (added, updated, removed), and the database is unchanged

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

### Requirement: Regions, states and metro areas are synced from the sheet
The sync SHALL read the sheet's `geo-filters_json` tab. Each row of the tab gives an area's filter type (`region`, `state` or `metro`), ID, label and home state, and one rule. A rule's match type is `state`, `county`, `city` or `any`, and its value is a comma-separated list. Rows with the same ID SHALL make up one area. After a sync, the stored areas SHALL be exactly those in the tab: areas that are new are added, areas that have changed are updated, and areas that are gone are removed. Areas SHALL be ordered by their first row in the tab. The `ALL` row (match type `any`) SHALL NOT be stored as an area.

#### Scenario: Metro with several rules
- **WHEN** the tab has three rows with ID `metro_MA_Boston`: a `state` rule "MA", a `city` rule "Brookline, Cambridge, Somerville" and a `county` rule "Suffolk"
- **THEN** one metro area "MA: Boston" is stored, with those states, cities and counties

#### Scenario: Area removed from the sheet
- **WHEN** an area that was stored by an earlier sync is no longer in the tab
- **THEN** the sync removes it, and it no longer appears as a filter option

#### Scenario: Unknown filter type or match type
- **WHEN** a row has a filter type or match type the sync doesn't recognize
- **THEN** the sync skips that row and prints a warning naming its ID

#### Scenario: Missing tab
- **WHEN** the `geo-filters_json` tab can't be read
- **THEN** the sync fails with an error naming the tab, and neither venues nor areas change

### Requirement: The sheet can be read with a Google service account
When the `GOOGLE_SERVICE_ACCOUNT_JSON` environment variable is set, the sync SHALL read the venue tab and the `geo-filters_json` tab through the Google Sheets API, signed in as the service account whose JSON key the variable holds, with read-only access. When the variable is not set, the sync SHALL read the sheet with the gog CLI, as before.

#### Scenario: Service account configured
- **WHEN** the sync runs with `GOOGLE_SERVICE_ACCOUNT_JSON` set to a valid key
- **THEN** it reads both tabs through the Sheets API, signed in with the read-only scope, and gog is not run

#### Scenario: No service account
- **WHEN** the sync runs without `GOOGLE_SERVICE_ACCOUNT_JSON`
- **THEN** it reads both tabs with gog, as before

### Requirement: Both ways of reading give the same rows
Reading with the service account and reading with gog SHALL produce the same rows from the same sheet: the header row gives the keys, and short rows are padded with blanks. Parsing, the dry run and the all-or-nothing transaction SHALL behave the same either way.

#### Scenario: Same rows either way
- **WHEN** the Sheets API returns a tab whose trailing empty cells are dropped, as gog's output does
- **THEN** the rows are padded to the header exactly as gog's are, and the venues and areas saved are the same

### Requirement: Sheet read errors say what to fix
When the sheet can't be read with the service account, the sync SHALL stop and change nothing, with an error saying what to fix: an invalid key, the Sheets API being disabled in the account's project, the sheet not being shared with the account (naming its email), or a missing tab (naming it).

#### Scenario: Invalid key
- **WHEN** `GOOGLE_SERVICE_ACCOUNT_JSON` isn't valid service-account JSON
- **THEN** the sync fails saying the variable isn't a valid service-account key, without echoing its contents, and nothing changes

#### Scenario: Sheet not shared with the account
- **WHEN** the Sheets API refuses access to the sheet
- **THEN** the sync fails with an error that names the tab and says to share the sheet with the service account's email, which it names, and nothing changes

#### Scenario: Sheets API disabled
- **WHEN** the Sheets API reports that it isn't enabled in the service account's project
- **THEN** the sync fails saying to enable the Google Sheets API, rather than to share the sheet, and nothing changes

#### Scenario: Missing tab
- **WHEN** the Sheets API reports that the `geo-filters_json` range doesn't exist
- **THEN** the sync fails with an error naming `geo-filters_json`, and neither venues nor areas change

### Requirement: Sheet read errors never expose credentials
No error, warning or log line from reading the sheet SHALL contain the private key, an access token or the raw key JSON.

#### Scenario: Nothing secret in the output
- **WHEN** any of these errors happens
- **THEN** neither the command's output nor its error contains the private key, the access token or the key JSON
