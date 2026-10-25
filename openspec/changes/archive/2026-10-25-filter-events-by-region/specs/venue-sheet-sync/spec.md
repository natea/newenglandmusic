## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: A sync is all or nothing and can be previewed
The sync SHALL apply all venue and area changes in one transaction. With `--dry-run` it SHALL report how many venues it would create and update, and how many areas it would add, update and remove, and save nothing.

#### Scenario: Dry run
- **WHEN** the sync runs with `--dry-run`
- **THEN** it reports the venue counts (created, updated) and the area counts (added, updated, removed), and the database is unchanged
