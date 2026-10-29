## ADDED Requirements

### Requirement: Artists, bands and memberships
The site SHALL keep `Artist` records, for a person or solo act, and `Band` records, for a group. Each SHALL have a name, an optional home town and state, an optional official website and Bandcamp URL, editors' notes, an optional import ID, and the MusicBrainz fields below. An artist SHALL be able to be a member of any number of bands, and a band to have any number of members. Each membership SHALL have an optional role, an optional start and end year, and its source: "import", "musicbrainz" or "editor". The same artist SHALL NOT be listed twice in one band.

#### Scenario: A member of two bands
- **WHEN** an artist is added as the drummer of one band and the singer of another
- **THEN** both bands list them, each with its own role

#### Scenario: A former member
- **WHEN** a membership has the end year 2019
- **THEN** the band lists the artist as a former member

### Requirement: Import from a CSV file or a Google Sheet tab
`import_artists` SHALL read rows from a CSV file (`--csv <path>`) or a Google Sheet tab (`--sheet <id> --tab <name>`), in one layout with the columns `Act_ID`, `Name`, `Kind` ("artist" or "band"), `Members`, `Town`, `State`, `Website`, `Bandcamp`, `MusicBrainz_ID` and `Notes`. Rows SHALL be keyed by `Act_ID`: a row with a new ID creates a record, and one with a known ID updates it. `Members`, for a band, SHALL list its members separated by semicolons (not counting one inside a role's parentheses), each optionally followed by a role in parentheses ("Kim Gordon (bass)"); an entry that isn't a name with an optional role SHALL be reported and skipped; a member SHALL be matched to an existing artist with that name, or created. An artist's own row SHALL take over the record made for them as a member, when exactly one artist has that name and no `Act_ID`. The import SHALL only set the fields its columns hold, SHALL NOT delete any record or membership, and SHALL NOT overwrite a field an editor or MusicBrainz set, nor remove a membership from MusicBrainz or an editor. A row it can't use (no ID, no name, an unknown kind) SHALL be reported and skipped. `--dry-run` SHALL report what it would do and save nothing. The sheet SHALL be read with the `gog` CLI locally and with the service account on a server, as the venue sheet is.

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

### Requirement: Enrichment from MusicBrainz
`enrich_artists_from_musicbrainz` SHALL find each artist's and band's MusicBrainz artist and store its ID, and from it: its type, country, area, begin and end dates, genres, and links to its official website, Bandcamp, Wikidata and Discogs. A record SHALL keep its own website or Bandcamp URL where it already has one. For a band, it SHALL add the members MusicBrainz lists, with their roles and years, as memberships with the source "musicbrainz", matching each member to an artist with that MusicBrainz ID, then to one with that name and no MusicBrainz ID, and otherwise creating one. A record with a MusicBrainz ID from the import or an editor SHALL be looked up by that ID rather than searched for. A search SHALL be accepted only when exactly one candidate's name (or alias) matches the record's and it is the right kind (a person for an artist, a group for a band) and, for a record with a state, MusicBrainz doesn't place it only outside the US (by its area or its begin area), or when the evidence below picks one; otherwise the record SHALL be marked "ambiguous" or "not found", with the time it was checked. It SHALL make at most one MusicBrainz request a second, send the contact user agent, accept `--limit`, `--refresh` and `--dry-run`, and skip records checked before unless refreshing.

#### Scenario: A clear match
- **WHEN** a band "Krill" is searched for, and MusicBrainz has one group named "Krill", in Boston
- **THEN** the band stores that MusicBrainz ID, its area, its dates and its links, and gains its listed members

#### Scenario: A lone namesake elsewhere
- **WHEN** a band "Horse" in Massachusetts is searched for, and MusicBrainz's only group named "Horse" is from the United Kingdom
- **THEN** the band is marked "not found", and nothing from MusicBrainz is stored

#### Scenario: A lone match who moved
- **WHEN** an artist "Kim Deal" with the state OH is searched for, and MusicBrainz's only person named "Kim Deal" lives in Boston and was born in Dayton
- **THEN** the artist is matched to her

#### Scenario: A name several acts share
- **WHEN** MusicBrainz has three groups named "Horse" and no evidence picks one
- **THEN** the band is marked "ambiguous", and nothing from MusicBrainz is stored

#### Scenario: An ID given in the import
- **WHEN** a row gives a `MusicBrainz_ID`
- **THEN** enrichment looks that artist up by ID and doesn't search

#### Scenario: Members already known
- **WHEN** MusicBrainz lists a member who is already an artist with that MusicBrainz ID
- **THEN** that artist is linked, not duplicated

### Requirement: Last.fm is evidence only
When a name matches several MusicBrainz candidates of the right kind, enrichment MAY ask Last.fm about the name, and SHALL accept a candidate when Last.fm's page for the name gives that candidate's MusicBrainz ID and its bio doesn't say several acts share the name, or when exactly one candidate's MusicBrainz area or begin area is in a state the site covers. Nothing from Last.fm SHALL be stored or shown: not its bio, listeners, tags, images or URLs. Without a Last.fm key, enrichment SHALL go on without this evidence.

#### Scenario: Last.fm picks the candidate
- **WHEN** a name matches two MusicBrainz groups, and Last.fm's page for it gives the MusicBrainz ID of one, with no note of a shared name
- **THEN** that group is accepted, and nothing from Last.fm is saved

#### Scenario: A covered area picks the candidate
- **WHEN** a name matches two MusicBrainz groups, one from Providence, RI and one from Leeds
- **THEN** the Providence group is accepted

### Requirement: Bandcamp only as a link
The site SHALL NOT request anything from Bandcamp. A record's Bandcamp URL SHALL come only from an editor, the import, or MusicBrainz's links, and SHALL be accepted only when it's an `https` URL on `bandcamp.com` or a subdomain of it.

#### Scenario: A Bandcamp link from MusicBrainz
- **WHEN** MusicBrainz lists a band's Bandcamp page
- **THEN** the band stores that URL, and no request is made to Bandcamp

#### Scenario: Not a Bandcamp URL
- **WHEN** an import row's `Bandcamp` is "https://example.com/krill"
- **THEN** the row's Bandcamp URL is reported as invalid and not saved, and the rest of the row is imported

### Requirement: Admins manage the records
The admin SHALL list artists and bands with their town, state and MusicBrainz status, filter them by state and by status, and search them by name. A band's page SHALL show its members inline, and an artist's page the bands they're in. An admin SHALL be able to set a record's MusicBrainz ID by hand, which marks it as the editor's and keeps later enrichment from replacing it, and to clear a match so the next run searches again. A field an admin edits SHALL be marked as the editor's, so the import doesn't overwrite it. MusicBrainz's genres SHALL be credited to MusicBrainz where they're shown.

#### Scenario: Setting the MusicBrainz ID by hand
- **WHEN** an admin sets an "ambiguous" band's MusicBrainz ID and the enrichment runs with `--refresh`
- **THEN** the band is looked up by that ID, and its ID isn't replaced

#### Scenario: Members inline
- **WHEN** an admin opens a band
- **THEN** its members are listed with their roles, years and sources, and can be added or removed
