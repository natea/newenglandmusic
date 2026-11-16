## ADDED Requirements

### Requirement: The official genre list
The site SHALL keep one official list of genres in two levels: the 20 main genres and the sub-genres under each, exactly as supplied in issue #133. Every sub-genre SHALL belong to exactly one main genre. The list SHALL exist after every deploy without manual steps, and editors SHALL be able to add, rename and retire entries in the admin.

#### Scenario: The list is loaded
- **WHEN** the database is migrated
- **THEN** the 20 main genres exist, each with the sub-genres listed under it in issue #133 (Jazz includes Big Band, Folk includes Traditional Folk)

#### Scenario: Migrating again changes nothing
- **WHEN** the database is migrated a second time
- **THEN** no genre is duplicated, and a genre an editor renamed or retired keeps that change

#### Scenario: A genre with a main genre
- **WHEN** an editor opens the sub-genre "Celtic" in the admin
- **THEN** its main genre is shown as "International"

### Requirement: Venues and acts are tagged from the list
An editor SHALL be able to tag a venue, a band or an artist with any number of genres from the list, in the admin, by picking entries. Free text SHALL NOT create a genre through the tag picker. A tag on a sub-genre SHALL also count as a tag on its main genre wherever genres are matched.

#### Scenario: Tagging a venue
- **WHEN** an editor tags a venue with "Bluegrass" and "Folk Rock"
- **THEN** the venue is saved with those two tags and counts as tagged "Country" and "Folk"

#### Scenario: Retired genres are not offered
- **WHEN** an editor retires "Tribal" and opens a venue's tag picker
- **THEN** "Tribal" is not offered, and a venue already tagged with it keeps the tag until an editor removes it

### Requirement: Existing genre words are matched to the list
A `match_genres` command SHALL map each venue's sheet genre words and each act's MusicBrainz genre tags to list entries, by exact match on a name (ignoring case, spacing and punctuation) or by an alias table kept in the repository. It SHALL support `--dry-run`. It SHALL NOT guess: a word with no exact or alias match SHALL be left unmatched. The word `ALL` SHALL add no tags.

#### Scenario: Exact and alias matches
- **WHEN** a venue's genre words are "Jazz" and "Hip Hop", and the alias table maps "Hip Hop" to the sub-genre "Hip Hop"
- **THEN** the venue is tagged "Jazz" and "Hip Hop"

#### Scenario: A word that fits nothing
- **WHEN** an act's MusicBrainz tags are "jangle pop" and "indie rock", and only "indie rock" matches the list
- **THEN** the act is tagged "Indie Rock", and "jangle pop" is recorded as unmatched for that act

#### Scenario: An editor's tags are kept
- **WHEN** an editor has tagged a venue by hand and the command runs on a venue whose words suggest other genres
- **THEN** the editor's tags are unchanged and no tags are added or removed

#### Scenario: Dry run
- **WHEN** the command runs with `--dry-run`
- **THEN** it reports what it would tag and what it would leave unmatched, and saves nothing

#### Scenario: ALL adds nothing
- **WHEN** a venue's genre words are only "ALL"
- **THEN** the venue gets no tags and is not listed as unmatched

### Requirement: Unmatched words are shown to editors
The unmatched words SHALL be written to a review CSV with how many venues and acts use each, and SHALL be visible in the admin on each venue and act, so an editor can tag by hand or add an alias. Nothing SHALL be dropped: the original words stay stored and unchanged.

#### Scenario: Review file
- **WHEN** the command finishes with two unmatched words
- **THEN** the review CSV has one row per word with its count of venues and of acts

#### Scenario: Original words remain
- **WHEN** the command has run
- **THEN** every venue's and act's stored genre words are exactly as before

### Requirement: The sheet sync and enrichment leave tags alone
`sync_venues_from_gsheets` and `enrich_artists_from_musicbrainz` SHALL keep updating the stored genre words, and SHALL NOT add, change or remove genre tags.

#### Scenario: Sheet sync
- **WHEN** the sheet sync updates a venue whose genre words changed
- **THEN** the venue's words are updated and its tags are unchanged

#### Scenario: Enrichment
- **WHEN** enrichment refreshes an act's MusicBrainz tags
- **THEN** the act's genre tags are unchanged
