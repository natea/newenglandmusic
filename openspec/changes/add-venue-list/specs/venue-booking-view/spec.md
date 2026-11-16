## ADDED Requirements

### Requirement: Each venue has an artist view beside its fan page
Each venue that has a page SHALL have an artist view at `/venues/<slug>/booking`. The fan page and the artist view SHALL each show a pair of tabs, "For fans" and "For artists", linking to each other, with the current one marked. A venue that answers 404 on its fan page (marked inactive, or no such slug) SHALL answer 404 here too.

#### Scenario: Switching views
- **WHEN** a visitor on `/venues/obriens` follows "For artists"
- **THEN** they arrive at `/venues/obriens/booking`, where "For artists" is marked and "For fans" links back

#### Scenario: Inactive or unknown venue
- **WHEN** a visitor opens the artist view of an inactive venue or an unknown slug
- **THEN** the site answers 404

### Requirement: The artist view says whether the venue takes bookings
The artist view SHALL lead with the venue's name and one plain statement: "Takes open bookings", "Doesn't take open bookings", or "Not known". A venue with no booking details at all SHALL say none are known yet and link to its website when it has one.

#### Scenario: Nothing known
- **WHEN** a venue has no booking fields and no website
- **THEN** the view says no booking details are known yet and draws no empty fields

### Requirement: The artist view shows how to book the venue
Below the statement, the artist view SHALL show, each only when known: the booking type in plain words with a one-line meaning, how to apply as a link (the booking link, or else the website), the booking notes, open mic, the size of the room, and the genres and niche notes it books. A field with no value SHALL NOT be drawn.

#### Scenario: Open booking with a link and notes
- **WHEN** O'Brien's takes open bookings, has a booking link and notes, and books "Submit an Artist"
- **THEN** its artist view says "Takes open bookings", explains the booking type, links the booking link as how to apply, and shows the notes

#### Scenario: Falls back to the website
- **WHEN** a venue takes open bookings, has no booking link and has a website
- **THEN** how to apply links to its website

#### Scenario: Not known
- **WHEN** a venue's open booking is not known and its booking type is "Unknown"
- **THEN** the view says "Not known" and draws no booking type

#### Scenario: Closed booking
- **WHEN** a venue's open booking is "no" and its type is "Locals Only"
- **THEN** the view says it doesn't take open bookings and still shows the booking type and notes

### Requirement: The fan page leaves booking to the artist view
The fan page SHALL NOT show the booking type, booking link or booking notes; when the venue takes open bookings it SHALL link to the artist view in their place. Open mic, genres, size, age policy and access notes remain on the fan page.

#### Scenario: Open-booking venue
- **WHEN** a visitor opens the fan page of a venue that takes open bookings
- **THEN** the page links to "For artists" and shows no booking notes or booking link itself

### Requirement: The artist view stays out of search and reads well on phones
The artist view SHALL ask search engines not to index it, SHALL NOT be in the sitemap, SHALL have a title and description naming the venue and "booking", and SHALL fit a 390px-wide screen with no sideways scrolling.

#### Scenario: Not indexed
- **WHEN** a search engine fetches an artist view
- **THEN** the page asks not to be indexed

#### Scenario: Not in the sitemap
- **WHEN** a search engine fetches the sitemap
- **THEN** it lists no `/venues/<slug>/booking` address

#### Scenario: Title and description
- **WHEN** a visitor opens O'Brien's artist view
- **THEN** the title and meta description name O'Brien's and "booking"

#### Scenario: Narrow screen
- **WHEN** the artist view is rendered
- **THEN** a browser test at 390px finds nothing that scrolls sideways
