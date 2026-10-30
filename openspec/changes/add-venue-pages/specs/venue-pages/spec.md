## Purpose

Gives every active venue a public page that reads as the room's own show bill, so fans see what's on and musicians see what the room books and how to ask, on one page.

## ADDED Requirements

### Requirement: Every active venue has a page
Each venue SHALL have a page at `/venues/<slug>`, where the slug is made from its name (with its town added when another venue has the same name) and is unique. A venue the sheet marks inactive SHALL answer 404, as SHALL an unknown slug. A venue whose status is unknown SHALL have a page. The sheet sync SHALL NOT change a venue's slug.

#### Scenario: An active venue
- **WHEN** a visitor opens `/venues/obriens`
- **THEN** the site answers with O'Brien's page

#### Scenario: Two venues with one name
- **WHEN** two venues are both named "The Bar", one in Burlington, VT and one in Portland, ME
- **THEN** their slugs differ, one carrying its town

#### Scenario: Inactive or unknown
- **WHEN** a visitor opens the page of a venue marked inactive, or a slug no venue has
- **THEN** the site answers 404

### Requirement: The bill leads
Directly under the venue's name and its fact line, the page SHALL list every upcoming approved show at the venue, in date and time order, under the heading "The bill" with how many shows there are. Each night SHALL show its date with the day number most prominent, the headliner, the openers after "with", and the start time, and SHALL link to the event's page. Today's shows SHALL be marked. Headliner and openers SHALL be read as the listings read them (`event-listing`). A venue with no upcoming approved shows SHALL say so in one line in place of the bill.

#### Scenario: Nights in order
- **WHEN** O'Brien's has Subfobias at 2 p.m. and Motörhead at 7 p.m. on Oct 31, and Armus on Nov 1
- **THEN** the bill lists them in that order, Subfobias with its openers after "with", each linking to its event page

#### Scenario: Unapproved shows
- **WHEN** a venue has an unapproved upcoming event
- **THEN** it isn't on the bill

#### Scenario: Nothing coming up
- **WHEN** a venue has no upcoming approved shows
- **THEN** the page says no upcoming shows are listed, and draws no bill

### Requirement: One fact line, and booking within reach
Above the bill, the page SHALL show one line with, each only when known: the kind and size of room, the neighborhood, town and state, a link to the venue on Google Maps, and the genres it books. When the venue takes new acts (open booking), the line SHALL end in a link to how to ask: its booking link, or else the booking section below.

#### Scenario: Open booking
- **WHEN** O'Brien's has open booking and a booking link
- **THEN** its fact line ends in an "Open booking" link to that booking link

#### Scenario: Closed booking
- **WHEN** a venue doesn't take new acts
- **THEN** its fact line has no booking link

### Requirement: Facts for musicians and for fans
Below the bill, the page SHALL show a "Playing here" section (booking type, booking link and notes, open mic, genres and niche notes, size) and a "Getting here" section (neighborhood, town and state, age policy, accessibility notes, family-friendly, LGBTQ+-friendly, the venue's website). A field the venue has no value for SHALL NOT be drawn, and a section with no fields SHALL NOT be drawn.

#### Scenario: A sparse venue
- **WHEN** a venue has only a town and a website
- **THEN** "Getting here" shows the town and website, and "Playing here" isn't drawn

### Requirement: No map drawn from Google's data
The page SHALL NOT draw a map from Google Places coordinates. Its location SHALL be text (neighborhood, town, state) with a link that opens the venue on Google Maps in a new tab.

#### Scenario: Location
- **WHEN** a visitor opens a venue page
- **THEN** the page shows the venue's neighborhood, town and state as text and a "Map" link to Google Maps, and no embedded map

### Requirement: Venue pages are reachable and stay out of search while unshared
The event page SHALL link its venue's name to the venue page, and the venue's admin page SHALL offer "View on site". The venue page SHALL ask search engines not to index it, and SHALL NOT be listed in the sitemap.

#### Scenario: From an event page
- **WHEN** a visitor opens an event at O'Brien's
- **THEN** "O'Brien's" links to `/venues/obriens`

#### Scenario: Not indexed
- **WHEN** a search engine fetches a venue page
- **THEN** the page asks not to be indexed

### Requirement: The page reads well on phones and to every visitor
The page SHALL fit a 390px-wide screen with no sideways scrolling, with the name, the fact line and the first night in the first screen; it SHALL have a title and description naming the venue and its town; and its colours SHALL meet the site's contrast.

#### Scenario: On a phone
- **WHEN** the page is opened 390px wide
- **THEN** the name, the fact line and the first night are in the first screen, and nothing scrolls sideways
