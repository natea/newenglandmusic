## ADDED Requirements

### Requirement: Records from the events' artist names
`import_artists_from_events` SHALL read the Artists column of every approved event, past and upcoming, split each into names as the Spotify matching does, and skip placeholders and names that are already an artist's or a band's (compared normalized). For each remaining name it SHALL search MusicBrainz for a person and for a group of that name, choosing among each kind's candidates by the rules enrichment uses (an exact name or alias; with several, a covered state, then Last.fm's MusicBrainz ID). A name matched as exactly one kind, with the other kind not found, SHALL become a record of that kind (an Artist for a person, a Band for a group) with its MusicBrainz ID, no `Act_ID`, and no other change. Every other name SHALL NOT be saved, and SHALL be written to a review CSV in the import layout, with `Act_ID` and `Kind` blank, the reason ("both a person and a group", "several with this name", "not on MusicBrainz"), the number of events naming it, and one of them. It SHALL accept `--limit`, `--dry-run` and `--review-csv <path>`, pace MusicBrainz at one request a second, stop when MusicBrainz stays busy (keeping the records made), and be recorded as a job run.

#### Scenario: A band
- **WHEN** an approved event's Artists are "Speedy Ortiz, Krill", and MusicBrainz has one group named "Speedy Ortiz" and no person by that name
- **THEN** a Band "Speedy Ortiz" is made with that group's MusicBrainz ID

#### Scenario: A person
- **WHEN** a name is the only MusicBrainz person called "Kim Deal", and no group has that name
- **THEN** an Artist "Kim Deal" is made with her MusicBrainz ID

#### Scenario: Both a person and a group
- **WHEN** MusicBrainz has a person and a group both named "Horse"
- **THEN** no record is made, and "Horse" is on the review list as "both a person and a group"

#### Scenario: Not on MusicBrainz
- **WHEN** a name matches nothing on MusicBrainz
- **THEN** no record is made, and it's on the review list as "not on MusicBrainz", with how many events name it and one of them

#### Scenario: Placeholders, repeats and existing records
- **WHEN** events name "TBA", name "Krill" twice, and a Band "Krill" already exists
- **THEN** none of them is searched for

#### Scenario: Only approved events
- **WHEN** an unapproved event names an act no approved event names
- **THEN** that name isn't searched for

#### Scenario: Dry run
- **WHEN** the command runs with `--dry-run`
- **THEN** it reports what it would make and writes the review list, and saves no record

#### Scenario: Importing the review list
- **WHEN** an editor fills in `Act_ID` and `Kind` on the review list and runs `import_artists --csv` with it
- **THEN** those names become records, and the review list's extra columns are ignored
