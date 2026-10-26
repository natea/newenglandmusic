## ADDED Requirements

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
