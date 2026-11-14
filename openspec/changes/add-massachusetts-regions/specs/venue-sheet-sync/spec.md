## REMOVED Requirements

### Requirement: Regions, states and metro areas are synced from the sheet
**Reason**: The venue sheet is retired as the source of the site's geography. Areas are defined in the site's own data (event-geo-filter, "A venue belongs to an area by its rules"), and Massachusetts's sub-regions can't be expressed in the sheet's rules.
**Migration**: The areas the sheet last loaded are copied into the site's area data as they are, apart from Massachusetts's seven metros, which the 28 sub-regions replace; the sync no longer reads the `geo-filters_json` tab, adds, changes or removes areas.

## MODIFIED Requirements

### Requirement: A sync is all or nothing and can be previewed
The sync SHALL apply all venue changes in one transaction. With `--dry-run` it SHALL report how many venues it would create and update, and save nothing.

#### Scenario: Dry run
- **WHEN** the sync runs with `--dry-run`
- **THEN** it reports the venue counts (created, updated), and the database is unchanged

### Requirement: Both ways of reading give the same rows
Reading with the service account and reading with gog SHALL produce the same rows from the same sheet: the header row gives the keys, and short rows are padded with blanks. Parsing, the dry run and the all-or-nothing transaction SHALL behave the same either way.

#### Scenario: Same rows either way
- **WHEN** the Sheets API returns a tab whose trailing empty cells are dropped, as gog's output does
- **THEN** the rows are padded to the header exactly as gog's are, and the venues saved are the same

### Requirement: The sheet can be read with a Google service account
When the `GOOGLE_SERVICE_ACCOUNT_JSON` environment variable is set, the sync SHALL read the venue tab through the Google Sheets API, signed in as the service account whose JSON key the variable holds, with read-only access. When the variable is not set, the sync SHALL read the sheet with the gog CLI, as before.

#### Scenario: Service account configured
- **WHEN** the sync runs with `GOOGLE_SERVICE_ACCOUNT_JSON` set to a valid key
- **THEN** it reads the venue tab through the Sheets API, signed in with the read-only scope, and gog is not run

#### Scenario: No service account
- **WHEN** the sync runs without `GOOGLE_SERVICE_ACCOUNT_JSON`
- **THEN** it reads the venue tab with gog, as before

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
- **WHEN** the Sheets API reports that the venue tab's range doesn't exist
- **THEN** the sync fails with an error naming the tab, and no venue changes

## ADDED Requirements

### Requirement: The sync runs only by hand
The sync SHALL NOT run on a schedule; it SHALL run only when someone runs it, for a one-off import. Run without `--dry-run`, it SHALL still update matching venues from the sheet as before, so it SHALL be run with `--dry-run` first to see what would change.

#### Scenario: Not in the daily job
- **WHEN** the daily job runs
- **THEN** it doesn't run the sync, and no venue changes from the sheet
