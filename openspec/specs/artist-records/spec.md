# artist-records Specification

## Purpose
TBD - created by archiving change add-artists-and-bands. Update Purpose after archive.

## Requirements

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

### Requirement: Introductions from MusicBrainz and Wikipedia
Enrichment SHALL store a matched record's MusicBrainz disambiguation note. For a matched record with a Wikidata ID, it SHALL find the English Wikipedia article Wikidata links to it, fetch that article's summary, and store its opening paragraph as plain text, word for word, with the article's URL, its revision and the time it was fetched; it SHALL accept the summary only when it's an ordinary article (not a disambiguation page) and Wikipedia says the article belongs to that Wikidata item. A record with no Wikidata ID or no English article SHALL have no Wikipedia text, and a later run that finds none SHALL remove an earlier one. No image from Wikipedia SHALL be stored. Wherever the text is shown, it SHALL be credited with a link to the article and to the CC BY-SA 4.0 licence. Requests to Wikidata and Wikipedia SHALL send the contact user agent and be paced.

#### Scenario: An act with a Wikipedia article
- **WHEN** a band matches the MusicBrainz group Speedy Ortiz, which links to a Wikidata item whose English article is "Speedy Ortiz"
- **THEN** the band stores the article's opening paragraph ("Speedy Ortiz is an American indie rock band from Northampton, Massachusetts…"), its URL and revision, and the admin shows it credited to Wikipedia under CC BY-SA 4.0

#### Scenario: A local act without an article
- **WHEN** a band's MusicBrainz artist has no Wikidata link, or its Wikidata item has no English article
- **THEN** the band stores only MusicBrainz's disambiguation note, and makes no request to Wikipedia

#### Scenario: The wrong article
- **WHEN** Wikipedia's summary is a disambiguation page, or belongs to another Wikidata item
- **THEN** nothing from it is stored

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

### Requirement: Photos and social links from Wikidata, Commons and MusicBrainz
For a matched record with a Wikidata ID, enrichment SHALL read the item's image (P18), Instagram username (P2003) and YouTube channel ID (P2397). For the image it SHALL fetch the file's licence and author from Wikimedia Commons and keep the file name, author, licence name and licence link only when the licence is free (public domain, CC0, CC BY or CC BY-SA); otherwise no photo. From MusicBrainz's links it SHALL also take an `instagram.com` link and a YouTube channel link. A record's Instagram and YouTube links SHALL be kept when an editor set them, and Wikidata's or MusicBrainz's otherwise. No image file SHALL be stored. Requests SHALL send the contact user agent and be paced.

#### Scenario: A free photo
- **WHEN** a band's Wikidata item has the image "Bonerama2006.jpg", which Commons lists under CC BY-SA 3.0 by a named author
- **THEN** the band keeps the file name, the author, "CC BY-SA 3.0" and its licence link

#### Scenario: A file without a free licence
- **WHEN** Commons gives no free licence for the file
- **THEN** the band keeps no photo

#### Scenario: Social links
- **WHEN** MusicBrainz lists `https://www.instagram.com/speedyortiz/` and Wikidata a YouTube channel ID
- **THEN** the band keeps both links

#### Scenario: An editor's link stays
- **WHEN** an editor set a band's Instagram link and enrichment finds another
- **THEN** the editor's link stays
