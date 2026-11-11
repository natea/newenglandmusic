## ADDED Requirements

### Requirement: The page plays the act's Bandcamp player
An artist or band page SHALL show Bandcamp's embedded player for an act with a usable player (see `bandcamp-embed`), in a section after the links titled "Listen on Bandcamp". Until the visitor presses its play button the page SHALL load nothing from Bandcamp.

#### Scenario: Band page with a player
- **WHEN** a visitor opens a band page whose band has a usable album player
- **THEN** the page has a "Listen on Bandcamp" section with a play button, and no Bandcamp frame yet

#### Scenario: Pressing play on a band page
- **WHEN** a visitor presses the play button
- **THEN** a frame loading `bandcamp.com/EmbeddedPlayer/album=<id>/…` replaces it, titled with the band's name

### Requirement: The listening section is drawn only when it works
The section SHALL NOT be drawn for an act with no usable player, including one whose Bandcamp URL changed since the player was found unless an editor set it. Without JavaScript the section SHALL be a link to the act's Bandcamp page.

#### Scenario: Band page with no player
- **WHEN** a visitor opens the page of an act with a Bandcamp link but no usable player
- **THEN** the page has no listening section, and the Bandcamp link stays among the links

#### Scenario: Band page without JavaScript
- **WHEN** a visitor without JavaScript opens the page
- **THEN** the section is a link to the act's Bandcamp page
