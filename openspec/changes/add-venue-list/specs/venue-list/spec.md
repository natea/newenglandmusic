## ADDED Requirements

### Requirement: A public list of venues
The site SHALL have a page at `/venues` listing every venue that isn't marked inactive, in alphabetical order by name ignoring case and a leading "The". Each entry SHALL show the venue's name linking to its page, its town and state (with neighborhood when known), and, each only when known, the kind and size of the room and its genres. A venue marked inactive SHALL NOT be listed. The site's menu SHALL link to the list.

#### Scenario: Alphabetical list
- **WHEN** a visitor opens `/venues` and the site has venues "The Sinclair", "Brighton Music Hall" and "O'Brien's"
- **THEN** the page lists Brighton Music Hall, O'Brien's, The Sinclair, in that order, each linking to its own page

#### Scenario: Menu link
- **WHEN** a visitor opens any page
- **THEN** the menu has a "Venues" item linking to `/venues`

#### Scenario: Inactive venue
- **WHEN** a venue is marked inactive in the sheet
- **THEN** it isn't in the list, and a venue whose status is unknown is

#### Scenario: A sparse venue
- **WHEN** a venue has only a name and a town
- **THEN** its entry shows the name and town and draws no empty kind, size or genre

### Requirement: Narrow the list by place and genre
The list SHALL offer the homepage events' place filters (same URL parameters) and a genre filter. Venues listing "ALL" SHALL match every genre, genre choices SHALL ignore case, unknown values SHALL be ignored, and a filter matching nothing SHALL say so with a way to clear it. Clearing the place SHALL keep the other filters.

#### Scenario: By town
- **WHEN** a visitor chooses the Boston metro area and the town Somerville, MA
- **THEN** only venues in Somerville, MA are listed

#### Scenario: By genre
- **WHEN** a visitor chooses the genre Jazz
- **THEN** venues listing Jazz, and venues listing "ALL", are shown, and a venue listing only Funk isn't

#### Scenario: Place and genre together
- **WHEN** a visitor chooses the state Massachusetts and the genre Jazz
- **THEN** only Massachusetts venues that list Jazz or "ALL" are shown

#### Scenario: Nothing matches
- **WHEN** the chosen filters match no venue
- **THEN** the page says no venues match and offers "show all"

#### Scenario: Nothing matches on genre alone
- **WHEN** the only filter set is a genre or "Takes open bookings", and it matches no venue
- **THEN** the page says no venues match and offers a "show all" that clears it

#### Scenario: Show all keeps the other filters
- **WHEN** a visitor on `/venues?state=vermont&genre=Jazz` follows the place form's "show all"
- **THEN** the result is `/venues` with the place cleared and `genre=Jazz` still applied

#### Scenario: Choosing All for the place keeps the other filters
- **WHEN** a visitor with a remembered place opens `/venues?state=vermont&genre=Jazz` and chooses "All" in every place field
- **THEN** the remembered place is forgotten and the result is the unfiltered-by-place list with `genre=Jazz` still applied, with no redirect back to the old place

#### Scenario: Genre case
- **WHEN** one venue lists "jazz", another lists "Jazz", and a visitor chooses Jazz
- **THEN** both venues are listed, and Jazz appears once among the genre choices

#### Scenario: Changing the place keeps the other filters
- **WHEN** a visitor on `/venues?genre=Jazz&open_booking=1` chooses the state Vermont in the place form
- **THEN** the result is `/venues` with the state, `genre=Jazz` and `open_booking=1` all applied

#### Scenario: Unknown value
- **WHEN** a visitor opens `/venues?genre=No+Such+Genre`
- **THEN** the full list is shown

### Requirement: Artists can filter to venues that take open bookings
Under a separate "For artists" heading, the list SHALL offer a "Takes open bookings" filter that lists only venues marked as taking them (not those unknown or "no"), combined with the place and genre filters. With it on, each entry SHALL link to the venue's artist view and show its booking type when known. It SHALL be a URL parameter, so the result can be linked to.

#### Scenario: Open bookings only
- **WHEN** a visitor turns on "Takes open bookings" and one venue takes open bookings, one doesn't and one is unknown
- **THEN** only the venue that takes them is listed

#### Scenario: With a place filter
- **WHEN** "Takes open bookings" is on and the state is Vermont
- **THEN** only Vermont venues that take open bookings are listed

#### Scenario: Entry links go to the artist view
- **WHEN** "Takes open bookings" is on
- **THEN** each entry links to `/venues/<slug>/booking`

#### Scenario: Booking type shown
- **WHEN** "Takes open bookings" is on and a listed venue's booking type is "Submit an Artist"
- **THEN** its entry shows "Submit an Artist"

#### Scenario: Fan filters alone
- **WHEN** the filter is off
- **THEN** entries link to the fan page and the "For artists" heading still offers the filter

### Requirement: The place filter is remembered like the homepage's
The place filters SHALL share the homepage's remembered filter, as `event-geo-filter` now says. A visitor with a remembered place who opens `/venues` with none SHALL be sent to the list with it in the address, keeping any `genre` and `open_booking`. Genre and open booking SHALL NOT be remembered.

#### Scenario: Returning visitor
- **WHEN** a visitor who last filtered the homepage to Massachusetts opens `/venues`
- **THEN** they are sent to `/venues?state=massachusetts`

#### Scenario: Shared link keeps its filters
- **WHEN** a visitor whose cookie holds `state=massachusetts` opens `/venues?open_booking=1`
- **THEN** they are sent to `/venues?state=massachusetts&open_booking=1`

#### Scenario: Genre isn't remembered
- **WHEN** a visitor filters to Jazz and later opens `/venues`
- **THEN** the genre filter is not applied

### Requirement: The list reads well and stays out of search while unshared
The list SHALL fit a 390px-wide screen with no sideways scrolling and have a title and description naming venues. The page SHALL ask search engines not to index it, and SHALL NOT be in the sitemap, for as long as `add-venue-pages` does the same for venue pages; if `improve-sitemap`'s site-wide indexing switch lands, the list follows it.

#### Scenario: Not indexed
- **WHEN** a search engine fetches `/venues`
- **THEN** the page asks not to be indexed

#### Scenario: Not in the sitemap
- **WHEN** a search engine fetches the sitemap
- **THEN** it doesn't list `/venues`

#### Scenario: Title and description
- **WHEN** a visitor opens `/venues`
- **THEN** the page has a title and a meta description that name the venue list

#### Scenario: Narrow screen
- **WHEN** the list is rendered
- **THEN** a browser test at 390px finds nothing that scrolls sideways
