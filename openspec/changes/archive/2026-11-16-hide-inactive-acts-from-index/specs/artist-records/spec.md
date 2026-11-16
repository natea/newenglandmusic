## MODIFIED Requirements

### Requirement: Admins manage the records
The admin SHALL list artists and bands with their town, state and MusicBrainz status, filter them by state, by status, by source and by whether they're inactive, show each record's sources, and search them by name. A band's page SHALL show its members inline, and an artist's page the bands they're in. An admin SHALL be able to set a record's MusicBrainz ID by hand, which marks it as the editor's and keeps later enrichment from replacing it, and to clear a match so the next run searches again. A field an admin edits SHALL be marked as the editor's, so the import doesn't overwrite it. MusicBrainz's genres SHALL be credited to MusicBrainz where they're shown.

#### Scenario: Setting the MusicBrainz ID by hand
- **WHEN** an admin sets an "ambiguous" band's MusicBrainz ID and the enrichment runs with `--refresh`
- **THEN** the band is looked up by that ID, and its ID isn't replaced

#### Scenario: Members inline
- **WHEN** an admin opens a band
- **THEN** its members are listed with their roles, years and sources, and can be added or removed

#### Scenario: Filtering by source
- **WHEN** an admin filters bands by the source "ohb"
- **THEN** only bands from that list are shown, including ones that were also made from events

## ADDED Requirements

### Requirement: Editors mark acts inactive
Each band and artist SHALL carry an inactive mark, off by default, that editors set or clear in the admin: on the act's form, with a list filter, and with bulk actions "Mark inactive" and "Mark active". Imports and enrichment SHALL NOT set or clear it.

#### Scenario: Marking in the admin
- **WHEN** an editor selects two acts and runs "Mark inactive", then filters the list by inactive
- **THEN** both are inactive and the filter lists them, and "Mark active" reverses it

#### Scenario: Imports leave the mark alone
- **WHEN** an inactive act is imported again by `import_artists` or `import_act_list`, or enriched from MusicBrainz
- **THEN** it is still inactive

#### Scenario: Import ignores the column
- **WHEN** an exported file with an `is_inactive` column is read back in by `import_artists`
- **THEN** the import succeeds and no act's mark changes

### Requirement: A command marks acts inactive by address
`mark_inactive_acts` SHALL mark the bands and artists whose slugs it is given, as arguments or from `--file` (one per line, blank lines and lines starting with `#` ignored), inactive (active with `--active`), and with `--dry-run` change nothing. A bare slug matching both a band and an artist SHALL mark neither and be reported as ambiguous; `bands/slug` names the kind. It SHALL report the acts it changed and the addresses it didn't find, and record a job run.

#### Scenario: Marking by slug
- **WHEN** it is run with `the-cars` and `greg-humphreys`, a band and an artist
- **THEN** both are inactive and it prints both

#### Scenario: A dry run
- **WHEN** it is run with `--dry-run` and `the-cars`
- **THEN** it prints that it would mark the act, and the act is unchanged

#### Scenario: An unknown address
- **WHEN** it is run with `the-cars` and `no-such-band`
- **THEN** The Cars is marked, and `no-such-band` is listed as not found

#### Scenario: An ambiguous address
- **WHEN** a band and an artist both have the slug `orbit` and the command is run with `orbit`
- **THEN** neither is changed and `orbit` is reported as ambiguous

#### Scenario: A kind-qualified address
- **WHEN** a band and an artist both have the slug `orbit` and the command is run with `bands/orbit`
- **THEN** only the band is marked

#### Scenario: Addresses from a file
- **WHEN** it is run with `--file` naming a file that lists `the-cars` and `greg-humphreys`
- **THEN** both are marked, as if given as arguments

#### Scenario: Comments in the file
- **WHEN** the file has a `#` comment line, a blank line and `bands/the-cars`
- **THEN** only The Cars is marked and no address is reported as not found

#### Scenario: A job run
- **WHEN** it is run
- **THEN** a job run is recorded with the number of acts changed

#### Scenario: Reversing
- **WHEN** it is run with `--active` and `the-cars`
- **THEN** The Cars is active again
