## ADDED Requirements

### Requirement: A genre picker on the calendar and the acts index
The calendar listing (the home page and the month pages) and the bands and artists index SHALL offer a genre picker listing the main genres, with each main genre's sub-genres grouped beneath it. It SHALL work without JavaScript, as a plain form. Genres no listed show or act carries SHALL NOT be offered.

#### Scenario: Picker contents
- **WHEN** a visitor opens the calendar
- **THEN** the picker offers "All genres" and the main genres that some listed show carries, with their used sub-genres grouped under them

#### Scenario: Main genre offered for a used sub-genre
- **WHEN** only "Big Band" is carried by a listed show
- **THEN** the picker offers a "Jazz" group containing "All Jazz" and "Big Band"

#### Scenario: Unused genres are not offered
- **WHEN** no show in the listing carries "Mariachi"
- **THEN** "Mariachi" is not offered on the calendar's picker

### Requirement: A main genre includes its sub-genres
Picking a main genre SHALL show everything tagged with that genre or any of its non-retired sub-genres. Picking a sub-genre SHALL show only what is tagged with that sub-genre.

#### Scenario: Main genre
- **WHEN** a visitor picks "Jazz" and one show's venue is tagged "Big Band" and another's is tagged "Blues"
- **THEN** the Big Band show is listed and the Blues show is not

#### Scenario: Retired sub-genre
- **WHEN** a visitor picks "Jazz" and a show's venue is tagged only with a retired sub-genre of Jazz
- **THEN** the show is not listed, and the picker does not offer the retired sub-genre

#### Scenario: Sub-genre
- **WHEN** a visitor picks "Big Band" and one show's venue is tagged "Big Band" and another's "Swing"
- **THEN** only the first is listed

### Requirement: A show matches through its venue or its acts
A show on the calendar SHALL match a genre when its venue carries it, or when any act billed on it (a band or artist linked to the event) carries it. A show SHALL appear once however many of its acts match.

#### Scenario: Matching by billed act
- **WHEN** a visitor picks "Reggae" and a show's venue has no genre tags but one of its billed bands is tagged "Ska"
- **THEN** the show is listed

#### Scenario: Listed once
- **WHEN** a show's venue and two of its acts all carry the picked genre
- **THEN** the show is listed once

#### Scenario: An act held for review
- **WHEN** a band marked as needing review carries the picked genre and bills on a show whose venue does not
- **THEN** the show is not listed because of that band

### Requirement: The genre is in the address
The picked genre SHALL be the `genre` value in the page's address, as the genre's slug. It SHALL NOT be remembered in a cookie, and SHALL combine with the state and metro filter. Links between months, and the redirect to a remembered state or metro filter, SHALL keep it. An unknown value SHALL be ignored as if no genre were picked.

#### Scenario: Shared link
- **WHEN** someone opens the calendar at `?genre=jazz`
- **THEN** the page lists only jazz shows and the picker shows Jazz picked

#### Scenario: Not remembered
- **WHEN** a visitor picks "Jazz" and later opens the calendar without a genre in the address
- **THEN** all genres are listed

#### Scenario: Combined with state
- **WHEN** a visitor has the Vermont filter and picks "Folk"
- **THEN** only folk shows in Vermont are listed

#### Scenario: Month links
- **WHEN** a visitor on `?genre=jazz` follows the next-month link
- **THEN** the next month's page also lists only jazz shows

#### Scenario: Old address kept
- **WHEN** a visitor opens `/artists?genre=folk`
- **THEN** they are redirected to `/bands?genre=folk`

#### Scenario: Unknown genre
- **WHEN** the address has `?genre=not-a-genre`
- **THEN** all shows are listed

#### Scenario: Retired genre
- **WHEN** the address has the slug of a retired genre
- **THEN** all shows are listed

#### Scenario: Clearing the state keeps the genre
- **WHEN** a visitor with a remembered Vermont filter and `genre=jazz` picked sets the state to "All"
- **THEN** the remembered filter is cleared, jazz shows from every state are listed, and the genre stays picked

#### Scenario: Show all clears both
- **WHEN** a visitor with a genre picked follows the "show all" link
- **THEN** neither the geo filter nor the genre applies

#### Scenario: Not offered on discover
- **WHEN** a visitor opens the discover page
- **THEN** it has no genre picker and ignores a `genre` value in the address (it lists as if none were given)

### Requirement: No matches is said plainly
When the picked genre leaves nothing to list, the page SHALL say no shows match, and offer to clear the genre.

#### Scenario: Empty result
- **WHEN** a visitor picks a genre no upcoming show carries (with or without a state filter)
- **THEN** the page says no shows match and links to the same page without the genre, keeping any state or metro filter

### Requirement: The acts index filters by genre
On the bands and artists index, picking a genre SHALL list only the live acts tagged with it, or with a sub-genre of it when a main genre is picked, keeping the A to Z order and counts.

#### Scenario: Acts by main genre
- **WHEN** a visitor picks "Folk" on the index and one act is tagged "Folk Rock" and another "Metal"
- **THEN** only the Folk Rock act is listed, and the count reflects it

#### Scenario: Inactive and held acts
- **WHEN** an act tagged with the picked genre is inactive or needs review
- **THEN** the index lists it exactly as it would without the filter (inactive and held acts stay off)
