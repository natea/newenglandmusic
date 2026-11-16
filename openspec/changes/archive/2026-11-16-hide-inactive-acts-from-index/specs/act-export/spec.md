## MODIFIED Requirements

### Requirement: The file holds the shareable details of an act

Each row SHALL include the act's name, import ID, town, state, links (website, Bandcamp page, Instagram, YouTube, Discogs), notes, public page address, review status and reasons, whether the act is inactive, MusicBrainz details (ID, status, type, country, area, dates, disambiguation), Wikidata ID, sources and photo credit. A band's row SHALL list its members as "Name (role)" joined with semicolons, and an artist's row the bands they belong to. Cells with no value SHALL be blank.

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

#### Scenario: An inactive act

- **WHEN** an inactive act is exported
- **THEN** its inactive cell is true, and an active act's is false
