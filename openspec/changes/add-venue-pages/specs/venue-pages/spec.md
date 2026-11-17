## Purpose

Gives every active venue a public page that reads as the room's own show bill, so fans see what's on and musicians see what the room books and how to ask, on one page.

## ADDED Requirements

### Requirement: Every active venue has a page
Each New England venue SHALL have a page at `/venues/<slug>`, where the slug is made from its name (with its town added when another venue has the same name) and is unique. A venue marked inactive in the admin SHALL answer 404, as SHALL a venue outside New England and an unknown slug. A venue whose status is unknown SHALL have a page. Renaming a venue SHALL NOT change its slug; an editor MAY change the slug in the admin, and the manual sheet import SHALL NOT change it.

#### Scenario: An active venue
- **WHEN** a visitor opens `/venues/obriens`
- **THEN** the site answers with O'Brien's page

#### Scenario: Two venues with one name
- **WHEN** two venues are both named "The Bar", one in Burlington, VT and one in Portland, ME
- **THEN** their slugs differ, one carrying its town

#### Scenario: Inactive or unknown
- **WHEN** a visitor opens the page of a venue marked inactive, or a slug no venue has
- **THEN** the site answers 404

#### Scenario: Outside New England
- **WHEN** a visitor opens the page of a venue in New York
- **THEN** the site answers 404, as the listings hide its shows

#### Scenario: A renamed venue
- **WHEN** an editor renames O'Brien's in the admin
- **THEN** its page stays at `/venues/obriens`

### Requirement: The bill leads
Under the fact line, "The bill" (with its show count) SHALL list every upcoming approved show at the venue in date and time order. Each night SHALL show its date (the day number most prominent), the headliner, the openers after "with" (read as `event-listing` reads them) and the start time, and SHALL link to its event page. Today's shows SHALL be marked. With no upcoming approved shows, one line SHALL say so instead.

#### Scenario: Nights in order
- **WHEN** O'Brien's has Subfobias at 2 p.m. and Motörhead at 7 p.m. on Oct 31, and Armus on Nov 1
- **THEN** the bill lists them in that order, Subfobias with its openers after "with", each linking to its event page

#### Scenario: Unapproved shows
- **WHEN** a venue has an unapproved upcoming event
- **THEN** it isn't on the bill

#### Scenario: Nothing coming up
- **WHEN** a venue has no upcoming approved shows
- **THEN** the page says no upcoming shows are listed, and draws no bill

### Requirement: One fact line, and booking one tab away
Above the bill, the page SHALL show one line with, each only when known: the room's kind and size; neighborhood, town and state; the Massachusetts sub-region, linking to its listing; a Google Maps link; and the genres it books. Booking type, link and notes SHALL be on the artist view (`venue-booking-view`), not here. When the venue takes open bookings, the line SHALL end in a link to the artist view.

#### Scenario: Open booking
- **WHEN** O'Brien's takes open bookings and has a booking link and notes
- **THEN** its fact line ends in a link to `/venues/obriens/booking`, and the page shows neither the booking link nor the notes

#### Scenario: Closed booking
- **WHEN** a venue doesn't take new acts
- **THEN** its fact line has no booking link, and the "For artists" tab is still there

#### Scenario: The sub-region
- **WHEN** a visitor opens the page of a venue in Somerville, MA
- **THEN** its fact line names "North of the Charles", linking to `/?metro=ma-north-of-the-charles`

### Requirement: Facts for musicians and for fans
Below the bill, the page SHALL show a "Playing here" section (open mic, genres and niche notes, size) and a "Getting here" section (neighborhood, town and state, age policy, accessibility notes, family-friendly, LGBTQ+-friendly, the venue's website). A field the venue has no value for SHALL NOT be drawn, and a section with no fields SHALL NOT be drawn.

#### Scenario: A sparse venue
- **WHEN** a venue has only a town and a website
- **THEN** "Getting here" shows the town and website, and "Playing here" isn't drawn

### Requirement: No map drawn from Google's data
The page SHALL NOT draw a map from Google Places coordinates. Its location SHALL be text (neighborhood, town, state) with a link that opens the venue on Google Maps in a new tab.

#### Scenario: Location
- **WHEN** a visitor opens a venue page
- **THEN** the page shows the venue's neighborhood, town and state as text and a "Map" link to Google Maps, and no embedded map

### Requirement: Venue pages are reachable and can be found
The event page SHALL link its venue's name to the venue page, and the venue's admin page SHALL offer "View on site". The venue page SHALL be open to search engines, with a canonical link to itself.

#### Scenario: From an event page
- **WHEN** a visitor opens an event at O'Brien's
- **THEN** "O'Brien's" links to `/venues/obriens`

#### Scenario: Can be indexed
- **WHEN** a search engine fetches a venue page
- **THEN** the page carries no `noindex`, and its canonical link is its own address

### Requirement: The page reads well on phones and to every visitor
The page SHALL fit a 390px-wide screen with no sideways scrolling, with the name, the fact line and the first night in the first screen; it SHALL have a title and description naming the venue and its town; and its colours SHALL meet the site's contrast.

#### Scenario: On a phone
- **WHEN** the page is opened 390px wide
- **THEN** the name, the fact line and the first night are in the first screen, and nothing scrolls sideways
