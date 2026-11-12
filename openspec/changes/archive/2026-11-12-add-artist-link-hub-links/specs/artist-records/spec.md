## ADDED Requirements

### Requirement: Link-hub address in enrichment
Enrichment SHALL take a MusicBrainz link, of any type, on a supported link hub (see `artist-link-hubs`) as the record's link-hub address when the record has none or has one MusicBrainz set, and SHALL NOT replace an editor's. This is in addition to the links "Enrichment from MusicBrainz" takes (the hub link is none of its homepage, Bandcamp, Wikidata or Discogs links), so that requirement is not modified.

#### Scenario: Hub link among several links
- **WHEN** MusicBrainz lists a band's "social network" link on `linktr.ee` and one on `facebook.com`
- **THEN** the band's hub address is the Linktree one

### Requirement: Hub data survives clearing a match
The hub fields and the links filled from a hub SHALL survive clearing a MusicBrainz match, and the address SHALL stay marked as MusicBrainz's.

#### Scenario: Clearing a match
- **WHEN** an admin clears a band's MusicBrainz match, and the band's Instagram link was filled from its hub
- **THEN** the Instagram link and the hub's findings stay, and the hub address, if MusicBrainz's, stays marked as MusicBrainz's

## MODIFIED Requirements

### Requirement: Bandcamp only as a link
The site SHALL NOT request anything from Bandcamp. A record's Bandcamp URL SHALL come only from an editor, the import, MusicBrainz's links, or the record's link hub (see `artist-link-hubs`), and SHALL be accepted only when it's an `https` URL on `bandcamp.com` or a subdomain of it.

#### Scenario: A Bandcamp link from MusicBrainz
- **WHEN** MusicBrainz lists a band's Bandcamp page
- **THEN** the band stores that URL, and no request is made to Bandcamp

#### Scenario: Not a Bandcamp URL
- **WHEN** an import row's `Bandcamp` is "https://example.com/krill"
- **THEN** the row's Bandcamp URL is reported as invalid and not saved, and the rest of the row is imported

### Requirement: Photos and social links from Wikidata, Commons and MusicBrainz
For a matched record with a Wikidata ID, enrichment SHALL read the item's image (P18), Instagram username (P2003) and YouTube channel ID (P2397). For the image it SHALL fetch the file's licence and author from Wikimedia Commons and keep the file name, author, licence name and licence link only when the licence is free (public domain, CC0, CC BY or CC BY-SA); otherwise no photo. From MusicBrainz's links it SHALL also take an `instagram.com` link and a YouTube channel link. A record's Instagram and YouTube links SHALL be kept when an editor set them, and Wikidata's or MusicBrainz's otherwise. A link filled from the record's link hub SHALL be kept when Wikidata and MusicBrainz have none, and replaced by theirs when they do. No image file SHALL be stored. Requests SHALL send the contact user agent and be paced.

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

### Requirement: Import from a CSV file or a Google Sheet tab
`import_artists` SHALL read rows from a CSV file (`--csv <path>`) or a Google Sheet tab (`--sheet <id> --tab <name>`), in one layout with the columns `Act_ID`, `Name`, `Kind` ("artist" or "band"), `Members`, `Town`, `State`, `Website`, `Bandcamp`, `Instagram`, `YouTube`, `MusicBrainz_ID` and `Notes`; `Instagram` and `YouTube` SHALL fill the record's Instagram and YouTube links. Rows SHALL be keyed by `Act_ID`: a row with a new ID creates a record, and one with a known ID updates it. `Members`, for a band, SHALL list its members separated by semicolons (not counting one inside a role's parentheses), each optionally followed by a role in parentheses ("Kim Gordon (bass)"); an entry that isn't a name with an optional role SHALL be reported and skipped; a member SHALL be matched to an existing artist with that name, or created. An artist's own row SHALL take over the record made for them as a member, when exactly one artist has that name and no `Act_ID`. The import SHALL only set the fields its columns hold, SHALL NOT delete any record or membership, and SHALL NOT overwrite a field an editor or MusicBrainz set (a value filled from the record's link hub, see `artist-link-hubs`, counts as unset: the row's value replaces it and is marked "import"), nor remove a membership from MusicBrainz or an editor. A row it can't use (no ID, no name, an unknown kind) SHALL be reported and skipped. `--dry-run` SHALL report what it would do and save nothing. The sheet SHALL be read with the `gog` CLI locally and with the service account on a server, as the venue sheet is.

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

#### Scenario: A row replaces a hub fill
- **WHEN** a band's Instagram link was filled from its link hub, and the sheet's row has a different `Instagram`
- **THEN** the band's Instagram link is the row's, marked "import"

### Requirement: Importing a curated list of names
`import_act_list --source <key>` SHALL read a list from one or more CSV files (`--csv <path>`) or Google Sheet tabs (`--sheet <id> --tab <name>`, `--tab` repeatable) in the list's own columns: the act's name (`Artist` or `Name`), and optionally `City` or `Town`, `State` (a full state name or its two-letter code), `Website`, `Bandcamp`, `Instagram`, `YouTube`, `MusicBrainz ID` and `Kind`. For each name it SHALL decide the kind on MusicBrainz: with a MusicBrainz ID, a person SHALL make an artist and a group a band; without one, the name SHALL be searched as the events' names are, and exactly one group SHALL make a band and exactly one person an artist, with the list's `Kind` settling a name that is both. Rows naming the same act, within a tab or across tabs (the same name ignoring case, accents and punctuation, or the same MusicBrainz ID), SHALL be merged into one before any lookup, the first tab's values winning where they differ and each difference reported. An act already on the site, by its MusicBrainz ID or else by its name and kind, SHALL be found rather than made again. It SHALL fill only unset fields or its own, never an editor's or MusicBrainz's, and add its source; a value filled from the record's link hub (see `artist-link-hubs`) counts as unset, and the list's value replaces it. Every act on the list SHALL become a record, since the list is vetted. An act it can't settle cleanly SHALL be made held for review (see "Acts held for review stay off the site"), with each reason: not on MusicBrainz, several with the name, both kinds and no `Kind` (made as a band), an ID MusicBrainz doesn't have, an ID whose MusicBrainz act has a different name or is typed as neither a person nor a group (an act with no type takes the list's `Kind`), or a match MusicBrainz places only outside the states the site covers. Its kind SHALL be MusicBrainz's when known, else the list's `Kind`, else band. After importing, it SHALL link every approved event to the records its names are, as the events' import does, re-rendering each event whose links change. `--dry-run` SHALL report and save nothing, and `--limit` SHALL stop after that many names. The run SHALL be recorded as a job run.

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

#### Scenario: A list replaces a hub fill
- **WHEN** a band's Bandcamp link was filled from its link hub, and the list's row has a different `Bandcamp`
- **THEN** the band's Bandcamp link is the list's, marked with the list's source

