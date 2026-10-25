## ADDED Requirements

### Requirement: Results are saved per venue in the database
The check SHALL save each checked venue's result in the database: its URL, events page, best source, JSON-LD event count, iCal feed URL and event count, ticketing platforms, JavaScript flag, error and the time it was checked. A venue SHALL have at most one saved result, which each new check replaces. A run SHALL change only the results of the venues it checked. Saving a result SHALL NOT change the venue's own fields or re-render its events.

#### Scenario: First check of a venue
- **WHEN** the check runs for a venue with no saved result and finds an iCal feed with 12 events
- **THEN** the venue has one saved result with best source ical, the feed URL, 12 events and the check time

#### Scenario: Re-check replaces the result
- **WHEN** a venue saved as ical is checked again and its site now only has ticketing links
- **THEN** its one saved result has best source ticketing and the platforms found, and no iCal feed

#### Scenario: Partial run keeps other results
- **WHEN** results are saved for venues in NH and ME, and the check then runs with `--state NH`
- **THEN** the NH results are replaced and the ME results are unchanged

#### Scenario: Venue's own fields untouched
- **WHEN** a venue's result is saved
- **THEN** the venue's fields and its events' rendered HTML are unchanged

### Requirement: Results can be exported to and imported from CSV
The check SHALL write the results of the venues it checked to a CSV file when given `--csv <path>`, with the same columns as the previous report file: sheet_id, name, state, city_town, url, events_page, best_source, json_ld_events, ical_url, ical_events, platforms, js_heavy and error. A separate import command SHALL load such a CSV into the saved results, matching rows to venues by sheet_id and skipping rows whose venue doesn't exist. Imported results SHALL be marked as checked at the file's modification time. The import SHALL support a dry run.

#### Scenario: CSV export
- **WHEN** the check runs with `--csv sources.csv`
- **THEN** the results are saved in the database and also written to `sources.csv` with those columns

#### Scenario: Import an existing report
- **WHEN** the import command loads a CSV with rows for 3 existing venues and 1 unknown sheet ID
- **THEN** 3 results are saved, the unknown row is reported as skipped, and nothing is crawled

#### Scenario: Import dry run
- **WHEN** the import command runs with `--dry-run`
- **THEN** it reports how many results it would create and replace, and saves nothing

## MODIFIED Requirements

### Requirement: The check identifies itself honestly and can be scoped
The check SHALL send the user agent `Mozilla/5.0 (compatible; venue-db-event-check/1.0)`. It SHALL skip inactive venues unless asked to include them, and SHALL accept a state filter and a limit.

#### Scenario: State filter
- **WHEN** the check runs with `--state NH`
- **THEN** only active New Hampshire venues are checked, and only their saved results change
