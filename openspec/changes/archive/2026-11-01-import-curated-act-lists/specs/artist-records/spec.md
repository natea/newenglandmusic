## MODIFIED Requirements

### Requirement: Import from a CSV file or a Google Sheet tab
`import_artists` SHALL read rows from a CSV file (`--csv <path>`) or a Google Sheet tab (`--sheet <id> --tab <name>`), in one layout with the columns `Act_ID`, `Name`, `Kind` ("artist" or "band"), `Members`, `Town`, `State`, `Website`, `Bandcamp`, `Instagram`, `YouTube`, `MusicBrainz_ID` and `Notes`; `Instagram` and `YouTube` SHALL fill the record's Instagram and YouTube links. Rows SHALL be keyed by `Act_ID`: a row with a new ID creates a record, and one with a known ID updates it. `Members`, for a band, SHALL list its members separated by semicolons (not counting one inside a role's parentheses), each optionally followed by a role in parentheses ("Kim Gordon (bass)"); an entry that isn't a name with an optional role SHALL be reported and skipped; a member SHALL be matched to an existing artist with that name, or created. An artist's own row SHALL take over the record made for them as a member, when exactly one artist has that name and no `Act_ID`. The import SHALL only set the fields its columns hold, SHALL NOT delete any record or membership, and SHALL NOT overwrite a field an editor or MusicBrainz set, nor remove a membership from MusicBrainz or an editor. A row it can't use (no ID, no name, an unknown kind) SHALL be reported and skipped. `--dry-run` SHALL report what it would do and save nothing. The sheet SHALL be read with the `gog` CLI locally and with the service account on a server, as the venue sheet is.

#### Scenario: Importing a band with members
- **WHEN** a row has `Act_ID` A0001, `Name` "Krill", `Kind` "band" and `Members` "Jonah Furman (bass, vocals); Aaron Mendelsohn (guitar)"
- **THEN** a band "Krill" exists with two member artists and their roles

#### Scenario: A member with their own row
- **WHEN** a band's row lists "Jonah Furman", and a later row A0004 is the artist "Jonah Furman"
- **THEN** there is one Jonah Furman, with the `Act_ID` A0004, in the band

#### Scenario: Importing again
- **WHEN** the same sheet is imported twice
- **THEN** the second import creates nothing new and changes nothing

#### Scenario: An editor's change is kept
- **WHEN** an editor changed a band's website in the admin, and the sheet still has the old one
- **THEN** the import leaves the editor's website

#### Scenario: A bad row
- **WHEN** a row's `Kind` is "orchestra"
- **THEN** the import reports that row and skips it, and imports the others

#### Scenario: Instagram and YouTube columns
- **WHEN** a row has `Instagram` "https://instagram.com/27theband/" and `YouTube` "https://www.youtube.com/27boston"
- **THEN** the record's Instagram and YouTube links are those, unless an editor or MusicBrainz set them

### Requirement: Admins manage the records
The admin SHALL list artists and bands with their town, state and MusicBrainz status, filter them by state, by status and by source, show each record's sources, and search them by name. A band's page SHALL show its members inline, and an artist's page the bands they're in. An admin SHALL be able to set a record's MusicBrainz ID by hand, which marks it as the editor's and keeps later enrichment from replacing it, and to clear a match so the next run searches again. A field an admin edits SHALL be marked as the editor's, so the import doesn't overwrite it. MusicBrainz's genres SHALL be credited to MusicBrainz where they're shown.

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

### Requirement: Records remember the lists that name them
Each artist and band SHALL keep the set of sources that named it, as short keys (`ohb` for Sooz's Oh Hello Boston list). Importing a list SHALL add its key to every record it makes or finds, once, and SHALL NOT remove any key. A record made from events, or by hand, has no source keys unless a list later names it.

#### Scenario: A list names an act made from events
- **WHEN** the band "Dropkick Murphys", made from events, is on the list imported as "ohb"
- **THEN** it is the same record, with the source "ohb", and no second Dropkick Murphys is made

#### Scenario: Importing twice
- **WHEN** the same list is imported twice
- **THEN** every record it names has "ohb" once, and nothing new is made the second time

### Requirement: Importing a curated list of names
`import_act_list --source <key>` SHALL read a list from one or more CSV files (`--csv <path>`) or Google Sheet tabs (`--sheet <id> --tab <name>`, `--tab` repeatable) in the list's own columns: the act's name (`Artist` or `Name`), and optionally `City` or `Town`, `State` (a full state name or its two-letter code), `Website`, `Bandcamp`, `Instagram`, `YouTube`, `MusicBrainz ID` and `Kind`. For each name it SHALL decide the kind on MusicBrainz: with a MusicBrainz ID, a person SHALL make an artist and a group a band; without one, the name SHALL be searched as the events' names are, and exactly one group SHALL make a band and exactly one person an artist, with the list's `Kind` settling a name that is both. Rows naming the same act, within a tab or across tabs (the same name ignoring case, accents and punctuation, or the same MusicBrainz ID), SHALL be merged into one before any lookup, the first tab's values winning where they differ and each difference reported. An act already on the site, by its MusicBrainz ID or else by its name and kind, SHALL be found rather than made again. It SHALL fill only unset fields or its own, never an editor's or MusicBrainz's, and add its source. Every act on the list SHALL become a record, since the list is vetted. An act it can't settle cleanly SHALL be made held for review (see "Acts held for review stay off the site"), with each reason: not on MusicBrainz, several with the name, both kinds and no `Kind` (made as a band), an ID MusicBrainz doesn't have, an ID whose MusicBrainz act has a different name or is typed as neither a person nor a group (an act with no type takes the list's `Kind`), or a match MusicBrainz places only outside the states the site covers. Its kind SHALL be MusicBrainz's when known, else the list's `Kind`, else band. After importing, it SHALL link every approved event to the records its names are, as the events' import does, re-rendering each event whose links change. `--dry-run` SHALL report and save nothing, and `--limit` SHALL stop after that many names. The run SHALL be recorded as a job run.

#### Scenario: A row with a MusicBrainz ID
- **WHEN** a row is "'Til Tuesday" with MusicBrainz ID 8cf8869d-e066-4c94-b734-fe05749badf0, a group
- **THEN** a band "'Til Tuesday" is made with that ID and the source "ohb"

#### Scenario: A row found by name
- **WHEN** a row is "28 Degrees Taurus" with no ID, and MusicBrainz has exactly one group of that name
- **THEN** a band is made with that group's ID, its town, state and Bandcamp link from the row, and the source "ohb"

#### Scenario: Both kinds, settled by the list
- **WHEN** MusicBrainz has a person and a group named "Horse", and the row's Kind is "Band"
- **THEN** a band "Horse" is made with the group's ID

#### Scenario: Not on MusicBrainz
- **WHEN** a row is "3 1/2 Girls" with no Kind, and MusicBrainz has no act of that name
- **THEN** a band "3 1/2 Girls" is made with the source "ohb", held for review as "not on MusicBrainz", with its links from the row

#### Scenario: Matched to an act from elsewhere
- **WHEN** a row is "Sunburst" from Boston, MA, and the one MusicBrainz group named Sunburst is from Ohio
- **THEN** the band is made with that ID but held for review as "placed outside the Northeast"

#### Scenario: An ID for a different act
- **WHEN** a row is "27" with a MusicBrainz ID whose act is named "Twenty Seven Strings"
- **THEN** the band is made held for review as "MusicBrainz's name differs"

#### Scenario: An act on both tabs
- **WHEN** "Adam Sherman" is on "In Rotation" and on "2026 backlog", and the import reads both tabs
- **THEN** he is looked up once, one artist is made with the source "ohb", and a field the two rows give differently takes "In Rotation"'s value and is reported

#### Scenario: A name repeated on one tab
- **WHEN** a tab lists the same act twice, once as "The Dresden Dolls" and once as "Dresden Dolls"
- **THEN** one record is made

#### Scenario: No type on MusicBrainz
- **WHEN** a row is "Wire Lines" with Kind "Band" and a MusicBrainz ID whose act has no type recorded
- **THEN** a live band is made with that ID, its kind from the row

#### Scenario: State names
- **WHEN** a row's State is "Massachusetts"
- **THEN** the record's state is "MA"

#### Scenario: Existing events are linked
- **WHEN** an approved upcoming event's artists are "28 Degrees Taurus, Kim Deal", and the import makes the band "28 Degrees Taurus"
- **THEN** the event is linked to 28 Degrees Taurus, in billing order with Kim Deal, and its listing is re-rendered

#### Scenario: A dry run
- **WHEN** the list is imported with `--dry-run`
- **THEN** it reports what it would make, find and review, and saves nothing

### Requirement: Acts held for review stay off the site
An artist or band held for review SHALL have no public page (its address answers 404), SHALL NOT be linked to any event, and SHALL NOT be listed in the sitemap, until an editor marks it ready. The admin SHALL filter artists and bands by whether they need review, show each one's reasons, and offer a "Mark ready" action, which SHALL clear the hold and its reasons and link the approved events that name the act. Only a curated list's import SHALL hold an act; a record made from events, by hand, or already live SHALL NOT be held by it.

#### Scenario: Hidden while held
- **WHEN** the band "3 1/2 Girls" is held for review and an approved event lists "3 1/2 Girls"
- **THEN** `/bands/3-1-2-girls` answers 404 and the event isn't linked to it

#### Scenario: Marked ready
- **WHEN** an editor selects "3 1/2 Girls" in the admin's "Needs review" list and runs "Mark ready"
- **THEN** it no longer needs review, its page loads, and the event that lists it is linked to it

#### Scenario: A live act stays live
- **WHEN** the list names "Dropkick Murphys", already live from events, and its MusicBrainz match would have been held
- **THEN** Dropkick Murphys stays live, with the source "ohb" added
