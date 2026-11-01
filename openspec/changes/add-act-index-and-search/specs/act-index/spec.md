## Purpose

Lets visitors find any band or artist on the site, with or without an upcoming show: an A–Z index of every live act, and acts in the site's search.

## ADDED Requirements

### Requirement: An A–Z index of bands and artists
The site SHALL list every live band and artist at `/bands`, together, ordered by name ignoring a leading "The", grouped under their first letter (names starting with a digit or symbol under "#"), with a rail of the letters that have acts, each linking to its group. Each entry SHALL show the act's name linking to its page, whether it's a band or an artist, its home town and state when known, and the date of its next upcoming approved show when it has one. An act held for review SHALL NOT be listed. `/artists` SHALL redirect to `/bands`. The site's menu SHALL link to the index as "Bands & artists".

#### Scenario: Bands and artists together
- **WHEN** the site has the band "Belly" from Providence, RI and the artist "Anjimile" from Boston, MA
- **THEN** `/bands` lists Anjimile under A and Belly under B, each linking to its page, with its kind and town

#### Scenario: A leading "The" and digits
- **WHEN** the site has "The Atlantics" and "28 Degrees Taurus"
- **THEN** The Atlantics is listed under A, and 28 Degrees Taurus under #

#### Scenario: The next show
- **WHEN** Belly has an approved show on Nov 14 and Anjimile has none
- **THEN** Belly's entry shows Nov 14, and Anjimile's shows no date

#### Scenario: Held acts left out
- **WHEN** the band "3 1/2 Girls" is held for review
- **THEN** it isn't on the index

#### Scenario: The artists address
- **WHEN** a visitor opens `/artists`
- **THEN** they're redirected to `/bands`

### Requirement: Search finds bands, artists, venues and shows
A search SHALL list, in this order and each in its own section: the live bands and artists whose names contain the search words, the active venues whose names contain them, the shows it finds, and the pages it finds. Names SHALL be matched ignoring case, accents and punctuation. Each band or artist SHALL link to its page with its kind and town; each venue SHALL show its town and link to the venue's page, or to a search for its shows while venues have no page. Acts held for review and inactive venues SHALL NOT be listed. A section with no match SHALL NOT be shown.

#### Scenario: A band by name
- **WHEN** a visitor searches for "belly"
- **THEN** the results list the band Belly, linking to `/bands/belly`, above any shows that match

#### Scenario: A venue by name
- **WHEN** a visitor searches for "o'brien"
- **THEN** the results list the venue O'Brien's with its town, in a venues section above the shows

#### Scenario: No act matches
- **WHEN** a visitor searches for "karaoke"
- **THEN** the results show shows and pages only, with no acts section

### Requirement: The search box suggests as you type
Once two or more characters are typed, the search box SHALL suggest matches under it, grouped and labelled by kind: up to five bands and artists, up to five venues, and up to five upcoming approved shows (with their date and venue), each linking where its search result does. The suggestions SHALL be operable from the keyboard (arrow keys move through them, Enter opens the one chosen, Escape closes them) and announced to screen readers as a list of options. Enter with no suggestion chosen SHALL run the full search. Without JavaScript the box SHALL submit a full search. Held acts and inactive venues SHALL NOT be suggested.

#### Scenario: Suggestions by kind
- **WHEN** a visitor types "bel" into the search box
- **THEN** a list under it shows "Bands & artists" with Belly, and any venues and upcoming shows that match, each labelled

#### Scenario: Going straight to a band
- **WHEN** the visitor presses the down arrow to Belly and presses Enter
- **THEN** Belly's page opens

#### Scenario: Running the full search
- **WHEN** the visitor types "belly" and presses Enter without choosing a suggestion
- **THEN** the full search results for "belly" open

#### Scenario: Too short
- **WHEN** a visitor has typed one character
- **THEN** no suggestions are shown

#### Scenario: Without JavaScript
- **WHEN** a visitor's browser runs no JavaScript and they search for "belly"
- **THEN** the full search results open

### Requirement: The index reads well on phones
The index SHALL fit a 390px-wide screen with no sideways scrolling, its letter rail wrapping onto as many lines as it needs.

#### Scenario: On a phone
- **WHEN** `/bands` is opened 390px wide
- **THEN** the letter rail and the entries fit the width, and nothing scrolls sideways
