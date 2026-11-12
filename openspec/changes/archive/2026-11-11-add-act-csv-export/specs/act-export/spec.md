## ADDED Requirements

### Requirement: Staff can download the artist and band lists as CSV

The admin's Artist list and Band list SHALL each have an "Export to CSV" button. It SHALL download a UTF-8 CSV file, starting with a byte order mark, with one header row and one row per act of that kind, ordered as the list is, with a filename that includes the kind and the date. The file SHALL hold the acts the list is showing, including those held for review, whatever the page size.

#### Scenario: Export every artist

- **WHEN** a signed-in admin clicks the button on the unfiltered artist list, which has 3 artists
- **THEN** the response is a CSV download with a header row and 3 artist rows

#### Scenario: Export a filtered band list

- **WHEN** an admin filters the band list to the state "MA", which is 2 of 3 bands, and clicks the button
- **THEN** the file has a header row and only those 2 bands

#### Scenario: Export a searched list

- **WHEN** an admin searches the artist list for "kim" and clicks the button
- **THEN** the file has only the artists the search finds

#### Scenario: More acts than a page

- **WHEN** the list shows 100 acts per page and 250 bands match
- **THEN** the file has all 250 band rows

#### Scenario: Acts held for review

- **WHEN** the band list holds a band marked as needing review and is unfiltered
- **THEN** the file includes that band, with its review status shown

#### Scenario: Opens in Excel

- **WHEN** the file is opened in Excel
- **THEN** an artist named "Sinéad" shows its accented letter correctly

### Requirement: The file holds the shareable details of an act

Each row SHALL include the act's name, import ID, town, state, links (website, Bandcamp page, Instagram, YouTube, Discogs), notes, public page address, review status and reasons, MusicBrainz details (ID, status, type, country, area, dates, disambiguation), Wikidata ID, sources and photo credit. A band's row SHALL list its members as "Name (role)" joined with semicolons, and an artist's row the bands they belong to. Cells with no value SHALL be blank.

#### Scenario: Artist fields in the row

- **WHEN** an artist has a name, the town "Boston", the state "MA" and a MusicBrainz ID
- **THEN** its row has those values

#### Scenario: Band members

- **WHEN** a band has the members "Jonah Furman" (bass) and "Aaron Mendelsohn" with no role
- **THEN** its members cell reads "Jonah Furman (bass); Aaron Mendelsohn"

#### Scenario: An artist's bands

- **WHEN** an artist is the drummer of "Krill" and a member of "Mal Blum"
- **THEN** its bands cell names both bands

#### Scenario: A new field is not handed out by accident

- **WHEN** a field is added to the act model and is neither exported nor named as left out
- **THEN** the test suite fails until it is one or the other

### Requirement: Credit-bound and bookkeeping data is left out

The file SHALL NOT contain the Wikipedia introduction text, its revision or fetch time (CC BY-SA 4.0, which must be credited wherever shown), nor MusicBrainz's genre tags (CC BY-NC-SA, also to be credited). It SHALL NOT contain who set each field, or created and updated times.

#### Scenario: Wikipedia text and genres

- **WHEN** an act has a Wikipedia introduction and genres from MusicBrainz
- **THEN** neither appears anywhere in the file

### Requirement: Only staff who may view that kind of act can export

The export SHALL be available only to a signed-in staff user who has permission to view that kind of act. Anyone else, including signed-out visitors and staff without that permission, SHALL be refused, and no act data SHALL be sent. The button SHALL not be shown to them. Permission to view artists SHALL NOT allow exporting bands, nor the reverse.

#### Scenario: Signed-out visitor

- **WHEN** a visitor who isn't signed in requests the artist export address
- **THEN** they are sent to the admin login page and the response has no act data

#### Scenario: Staff without permission

- **WHEN** a staff user who may view bands but not artists requests the artist export
- **THEN** the response is a refusal with no artist data, and the artist list has no button

#### Scenario: Member of the admin group

- **WHEN** a staff user in the "admin" group clicks the button on the band list
- **THEN** the file downloads

### Requirement: Cells can't run as formulas

Text cells SHALL be guarded and quoted exactly as in the venue export: a cell starting with `=`, `+`, `-`, `@`, a tab or a carriage return gets a leading apostrophe, and text with commas, quotes or line breaks is quoted so each act stays on one row.

#### Scenario: Formula-like note

- **WHEN** an act's notes are `=HYPERLINK("http://example.com")`
- **THEN** the cell reads `'=HYPERLINK("http://example.com")` in the file

#### Scenario: Commas and line breaks

- **WHEN** an act's notes are "Seen live, great" over two lines
- **THEN** the file reads back with one row for that act and the full notes in one cell
