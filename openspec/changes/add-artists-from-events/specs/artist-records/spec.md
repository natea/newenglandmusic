## ADDED Requirements

### Requirement: Records from the events' artist names
`import_artists_from_events` SHALL read the title and Artists column of every approved event, past and upcoming, and split them into names as the Spotify matching does (`event_artist_names`: a title's tour and show words dropped), since every source puts the headliner in the title and leaves it out of the Artists column; it SHALL skip placeholders and names that are already an artist's or a band's (compared normalized). For each remaining name it SHALL search MusicBrainz for a person and for a group of that name, choosing among each kind's candidates by the rules enrichment uses (an exact name or alias; with several, a covered state, then Last.fm's MusicBrainz ID). A name matched as exactly one kind, with the other kind not found, SHALL become a record of that kind (an Artist for a person, a Band for a group) with its MusicBrainz ID, no `Act_ID`, and no other change. A duo billing (two names of two words or more joined by "&" or "and", as in "Louis Cole & Chiquita Magic") not on MusicBrainz as a whole SHALL have each of its acts looked up the same way instead, and only the acts not found SHALL go on the review list; when none is found, the billing SHALL go there whole, as it may be one band. Every other name SHALL NOT be saved, and SHALL be written to a review CSV in the import layout, with `Act_ID` and `Kind` blank, the reason ("both a person and a group", "several with this name", "not on MusicBrainz"), the number of events naming it, and one of them. It SHALL accept `--limit`, `--dry-run` and `--review-csv <path>`, pace MusicBrainz at one request a second, stop when MusicBrainz stays busy (keeping the records made), and be recorded as a job run.

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

#### Scenario: A headliner in the title
- **WHEN** an approved event is titled "Speedy Ortiz" with the Artists "Kim Deal"
- **THEN** both names are looked up, and the event links to both, Speedy Ortiz first

#### Scenario: Only approved events
- **WHEN** an unapproved event names an act no approved event names
- **THEN** that name isn't searched for

#### Scenario: Dry run
- **WHEN** the command runs with `--dry-run`
- **THEN** it reports what it would make and writes the review list, and saves no record

#### Scenario: A duo billing's acts
- **WHEN** one event's artists are "Kim Deal & Speedy Ortiz" and another's "Kim Deal & Dana Alden", and neither billing is on MusicBrainz, Kim Deal is a person there, Speedy Ortiz a group and Dana Alden not there
- **THEN** an artist "Kim Deal" and a band "Speedy Ortiz" are made, the first event is linked to both, and only "Dana Alden" is on the review list

#### Scenario: A billing with no act found
- **WHEN** an event's artists are "Dust Bowls and Jewish Souls", and neither it nor either half is on MusicBrainz
- **THEN** "Dust Bowls and Jewish Souls" is on the review list, and its halves aren't

#### Scenario: Importing the review list
- **WHEN** an editor fills in `Act_ID` and `Kind` on the review list and runs `import_artists --csv` with it
- **THEN** those names become records, and the review list's extra columns are ignored

### Requirement: Events link to their artists and bands
An event SHALL have any number of performers, each an artist or a band (exactly one of the two), in billing order, with the source "names" (linked from the event's Artists text) or "editor". The same artist or band SHALL NOT be a performer of one event twice. Linking an event from its names SHALL take the names of its title and Artists text as the Spotify matching does, skip placeholders, and link each name that exactly one artist or band has (compared normalized; a known name followed by occasion words, as in "Built to Spill Fall 2026 Tour", counts as that name), in the order the names come; a name with no record, or several, SHALL stay unlinked. It SHALL replace the event's earlier links from names and keep its editor's links. `import_artists_from_events` SHALL link every approved event after making records, and `fetch_events` SHALL link each event it saves (not in a dry run). The event admin SHALL list an event's performers in order, with autocomplete for artists and bands, to add, remove and reorder; a performer added there SHALL have the source "editor". The Artists text SHALL stay as it is, and nothing visitors see SHALL change.

#### Scenario: Several acts on one bill
- **WHEN** an event's Artists are "Pixies, Speedy Ortiz, Kim Deal", and Pixies and Speedy Ortiz are bands and Kim Deal an artist
- **THEN** the event's performers are Pixies, Speedy Ortiz and Kim Deal, in that order

#### Scenario: A name with no record
- **WHEN** an event's Artists are "Pixies, Dana and Alden", and no record is called "Dana and Alden"
- **THEN** the event's only performer is Pixies, and its Artists text is unchanged

#### Scenario: Two records with one name
- **WHEN** both an artist and a band are named "Horse"
- **THEN** an event naming "Horse" isn't linked to either

#### Scenario: The text changes
- **WHEN** a fetched event's Artists change from "Pixies, Krill" to "Pixies, Pile"
- **THEN** its performers from names become Pixies and Pile

#### Scenario: An editor's performer stays
- **WHEN** an editor adds Lake Street Dive to an event in the admin, and the event is fetched again
- **THEN** Lake Street Dive is still a performer, with the source "editor"

#### Scenario: Fetched events are linked
- **WHEN** `fetch_events` saves a new event whose Artists name a band that has a record
- **THEN** the event is linked to that band
