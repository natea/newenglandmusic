## Purpose

Lets visitors find any band or artist on the site, with or without an upcoming show: an A–Z index of every live act, and acts in the site's search.

## ADDED Requirements

### Requirement: An A–Z index of bands and artists
The site SHALL list every live band and artist at `/bands`, together, ordered by name ignoring a leading "The", grouped under their first letter (names starting with a digit or symbol under "#"), with a rail of the letters that have acts, each linking to its group. Each entry SHALL show the act's name linking to its page, whether it's a band or an artist, its home town and state when known, and the date of its next upcoming approved show when it has one. An act held for review SHALL NOT be listed. `/artists` SHALL redirect to `/bands`, and the index's and act pages' addresses typed with a trailing slash, or in the singular (`/band`, `/artist/...`), SHALL redirect to their own address. The site's menu SHALL link to the index as "Bands & artists".

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

#### Scenario: A trailing slash
- **WHEN** a visitor opens `/bands/` or `/bands/belly/`
- **THEN** they're redirected to `/bands` or `/bands/belly`

#### Scenario: The singular
- **WHEN** a visitor opens `/band` or `/artist/anjimile/`
- **THEN** they're redirected to `/bands` or `/artists/anjimile`

### Requirement: The index is set like a book's index
Each letter SHALL be set in pages of 40 entries, each page headed by its first and last names as guide words. A name starting "The" SHALL be printed inverted on the index ("Atlantics, The"), where it's filed; its own page and search keep the act's name.

#### Scenario: Pages and guide words
- **WHEN** a letter has 42 acts
- **THEN** they're set in two pages, of 40 and 2, each headed by its first and last names

#### Scenario: "The" names inverted on the index only
- **WHEN** the site has "The Atlantics"
- **THEN** the index prints "Atlantics, The", and its page and a search for it print "The Atlantics"

### Requirement: Search finds bands, artists, venues and shows
A search SHALL list, in this order and each in its own section: the live bands and artists whose names contain the search words, the active venues whose names contain them, the shows it finds (by words anywhere in them, or part of a title or the artists), and the pages it finds. Each band or artist SHALL show the date of its next upcoming show. Names SHALL be matched ignoring case, accents and punctuation. Each band or artist SHALL link to its page with its kind and town; each venue SHALL show its town and link to the venue's page, or to a search for its shows while venues have no page. Acts held for review and inactive venues SHALL NOT be listed. A section with no match SHALL NOT be shown.

#### Scenario: A band by name
- **WHEN** a visitor searches for "belly"
- **THEN** the results list the band Belly, linking to `/bands/belly`, above any shows that match

#### Scenario: A venue by name
- **WHEN** a visitor searches for "o'brien"
- **THEN** the results list the venue O'Brien's with its town, in a venues section above the shows

#### Scenario: No act matches
- **WHEN** a visitor searches for "karaoke"
- **THEN** the results show shows and pages only, with no acts section

### Requirement: Search lists shows compactly, upcoming first
The search results SHALL list the shows found as compact rows (date, title linking to the show, venue and town, and the show's icon row): upcoming ones first, soonest first, then past ones, newest first, each under its own heading.

#### Scenario: Upcoming shows, then past ones
- **WHEN** a search finds shows in 2 and 9 days and shows 3 and 30 days ago
- **THEN** the upcoming two are listed soonest first, then the past two newest first, as compact rows

### Requirement: The search box is at the top of every page
The search box SHALL be at the top of every page, under the site's name, not behind the menu. On the search results page it SHALL hold what was searched, and the page SHALL have no other search box.

#### Scenario: On every page
- **WHEN** a visitor opens any page
- **THEN** the search box is in view at the top, without opening the menu

#### Scenario: One box on the results page
- **WHEN** a visitor searches for "belly"
- **THEN** the results page has one search box, holding "belly", and it suggests as the others do

### Requirement: The search box suggests as you type
Once two or more characters are typed, the search box SHALL suggest matches under it, grouped and labelled by kind: up to five bands and artists, up to five venues, and up to five upcoming approved shows (with their date and venue), each linking where its search result does. Every suggestion SHALL say which kind of record it is (Band, Artist, Venue or Show), visibly on its row and in what screen readers announce, so a band and an artist of the same name, or a venue and a show named after it, can't be mistaken. The suggestions SHALL be operable from the keyboard (arrow keys move through them, Enter opens the one chosen, Escape closes them) and announced to screen readers as a list of options. Enter with no suggestion chosen SHALL run the full search. Without JavaScript the box SHALL submit a full search. Held acts and inactive venues SHALL NOT be suggested.

#### Scenario: Suggestions by kind
- **WHEN** a visitor types "bel" into the search box
- **THEN** a list under it shows "Bands & artists" with Belly tagged "Band", and any venues and upcoming shows that match, each group labelled

#### Scenario: Each suggestion says what it is
- **WHEN** a visitor types "paradise" and the suggestions include the venue Paradise Rock Club and a show there
- **THEN** the venue's row is tagged "Venue" and the show's row "Show", and a screen reader announces each with its kind ("Paradise Rock Club, venue")

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

### Requirement: What was searched is marked
In the suggestions and on the search results page, the part of each name or show title matching what was typed SHALL be marked, found as matching finds it (ignoring case, accents and punctuation), on the name's own characters.

#### Scenario: Marked in a suggestion
- **WHEN** a visitor types "bel" and Belly is suggested
- **THEN** "Bel" is marked in "Belly"

#### Scenario: Marked in the results, accents and all
- **WHEN** a visitor searches for "bel"
- **THEN** "Bel" is marked in Belly and "Bél" in Béla Fleck

### Requirement: The index reads well on phones
The index SHALL fit a 390px-wide screen with no sideways scrolling, its letter rail wrapping onto as many lines as it needs.

#### Scenario: On a phone
- **WHEN** `/bands` is opened 390px wide
- **THEN** the letter rail and the entries fit the width, and nothing scrolls sideways
