# Spec Delta

## Purpose
Describes what every public page shares: the header with the site's name, the search box and the main links; breadcrumbs; the footer; and the parts listing pages are built from (the rail beside a list, the show row, the week strip and the map link), including how they fold on smaller screens.

## ADDED Requirements

### Requirement: Every page has the same header
Every public page SHALL open with a header holding, in this order: the site's name linking to the home page; the search box; and four links, each an icon above its label, reading "Submit a show", "Saved", "Venues" and "Bands". The header SHALL have no menu that must be opened to reach those links, at any width.

#### Scenario: The header's parts
- **WHEN** a visitor opens the home page, a venue's page or the privacy page 1440px wide
- **THEN** each shows the name, the search box and the four links in that order, each link an icon above its label

#### Scenario: The links go where they say
- **WHEN** the visitor follows "Submit a show", "Saved", "Venues" and "Bands"
- **THEN** they open `/submit-event`, `/saved`, `/venues` and `/bands`

### Requirement: A rail can end with a call-out
The bands listing's rail SHALL end with a call-out headed "Not sure who to see?" linking to Discover bands. The venues listing's rail SHALL end with a call-out headed "Missing a venue?" linking to the page where a visitor suggests a venue. While the site has no such page, the "Missing a venue?" call-out SHALL NOT be shown.

#### Scenario: The bands listing
- **WHEN** a visitor opens `/bands`
- **THEN** its rail ends with "Not sure who to see?" and a link to `/discover`

#### Scenario: The venues listing, with a suggestion page
- **WHEN** the site has a page for suggesting a venue and a visitor opens `/venues`
- **THEN** its rail ends with "Missing a venue?" and a link to that page

#### Scenario: The venues listing, without one
- **WHEN** the site has no page for suggesting a venue
- **THEN** `/venues` shows no "Missing a venue?" call-out

### Requirement: Pages below the home page have breadcrumbs
Every public page other than the home page SHALL show, under the header, the path from the home page to itself: each step before the last as a link, the page itself last and not a link. A venue's page SHALL pass through "Venues"; a band's or artist's page through "Bands & artists"; a show's page through "Venues" and its venue when the venue has a page, ending with the headliner and the show's date.

#### Scenario: A show's page
- **WHEN** a visitor opens the page of Brookelen's show at O'Brien's on Nov 16
- **THEN** the breadcrumbs read "Home / Venues / O'Brien's / Brookelen, Nov 16", the first three as links

#### Scenario: A band's page
- **WHEN** a visitor opens Horse Jumper of Love's page
- **THEN** the breadcrumbs read "Home / Bands & artists / Horse Jumper of Love"

#### Scenario: The home page
- **WHEN** a visitor opens the home page
- **THEN** no breadcrumbs are shown

### Requirement: Listing pages keep their controls in a rail
The home page, the venues listing, the bands listing, search results and Saved shows SHALL show their controls in a rail beside the list, each group under a small caps label. The home page's rail SHALL hold the visitor's location with a way to change it ("Set your location" when none is saved), the area filters, the month calendar and the calendar subscription. The rail SHALL hold every filter the page already offers and no control that does nothing.

#### Scenario: The home page's rail
- **WHEN** a visitor whose saved location is Medford, MA opens the home page 1440px wide
- **THEN** the rail shows "Medford, MA" with "Change", the region, state, metro and neighborhood filters, the month calendar and "Subscribe to this calendar"

#### Scenario: Changing the location
- **WHEN** the visitor chooses "Change", picks "Salem, MA" and saves
- **THEN** they're back on the home page and the rail reads "Salem, MA"

#### Scenario: No dead controls
- **WHEN** any page with a rail is opened
- **THEN** every control in its rail changes what the page shows or goes somewhere

### Requirement: The home page opens with today
The home page's list SHALL open with the first listed day's date in small caps over a large heading: "Tonight" when that day is today, otherwise the day's name. Beside it SHALL be the number of shows listed for that day and where they are: "near <location>" when the visitor has a saved location, "in <area>" when only an area filter is set, naming the narrowest area chosen, and "across New England" otherwise. Later days SHALL follow down the page, each under its own date heading.

#### Scenario: Tonight, near a location
- **WHEN** a visitor whose location is Medford, MA opens the home page on Monday, November 16, with 14 shows listed that day
- **THEN** the list opens with "Monday, November 16", "Tonight" and "14 shows near Medford"

#### Scenario: In an area
- **WHEN** a visitor with no location filters to the Greater Boston metro area
- **THEN** the count line ends "in Greater Boston"

#### Scenario: Later days
- **WHEN** the visitor scrolls past today's shows
- **THEN** Tuesday's shows follow under a heading naming Tuesday, November 17

### Requirement: A week strip shows the next seven days
Under the heading, the home page SHALL show a strip of seven days starting with the first listed day, each with its weekday, its date and the number of shows listed for it under the current filters. The first day SHALL be marked. Choosing a day SHALL bring that day's shows into view. A day with no shows SHALL say "No shows" and SHALL NOT be a link.

#### Scenario: Seven days with counts
- **WHEN** the home page is opened on Monday, November 16
- **THEN** the strip shows Mon 16 to Sun 22, each with its count, with Mon 16 marked

#### Scenario: Choosing a day
- **WHEN** the visitor chooses Fri 20
- **THEN** Friday's date heading and shows are in view

#### Scenario: Counts follow the filters
- **WHEN** the visitor filters to Rhode Island
- **THEN** each day's count is of Rhode Island shows only

### Requirement: A show is listed as a row
Wherever a list of shows appears (the home page, a month's page, Saved shows and upcoming shows in search results), each show SHALL be one row holding, in this order: its start time; its name with its openers or note beneath; its venue as a link with the venue's place, the distance from the visitor's location when one is saved, and the age policy beneath; then its price on the accent when it's ticketed, or "FREE"; and the control that saves it. A cancelled show's row SHALL say so and be struck through.

#### Scenario: A ticketed show
- **WHEN** Brookelen plays O'Brien's in Allston at 7:00 PM, 21+, from $15, and the visitor's location is 4.6 miles away
- **THEN** its row reads "7:00 PM", "Brookelen" over "with Leila Lamb, Husbands", "O'Brien's" over "Allston · 4.6 mi · 21+", and the price on the accent, followed by the save control

#### Scenario: A free show
- **WHEN** a show's price is free
- **THEN** its row says "FREE" with no accent behind it

#### Scenario: No location
- **WHEN** the visitor has no saved location
- **THEN** the row's venue line gives the place and ages with no distance

### Requirement: "Show on map" maps the shows listed
When a map tiles key is set and a day has at least one listed show at a located venue, that day's heading SHALL have a "Show on map" link. Choosing it SHALL open a map above that day's rows, with a pin for each of that day's listed shows at a located venue under the current filters, fitted to the pins, and a line saying how many of the day's listed shows are on the map. Choosing a pin SHALL name the show there, its venue and time, with a link to the show. The link SHALL then read "Hide map", and choosing it SHALL close the map. The map SHALL NOT load until it's opened. Without a tiles key, or when no listed show of the day can be pinned, no link SHALL be shown.

#### Scenario: Opening the map
- **WHEN** 14 shows are listed tonight, 12 of them at located venues, and the visitor chooses "Show on map"
- **THEN** a map opens above tonight's rows with pins for those 12, a line reading "12 of 14 shows on the map", and the link reads "Hide map"

#### Scenario: The map follows the filters
- **WHEN** the visitor has filtered to Cambridge and opens the map
- **THEN** only Cambridge shows are pinned

#### Scenario: A pin
- **WHEN** the visitor chooses the pin at O'Brien's
- **THEN** a callout reads "Brookelen", "O'Brien's · 7:00 PM" and links to the show

#### Scenario: Closing it
- **WHEN** the visitor chooses "Hide map"
- **THEN** the map closes and the link reads "Show on map"

#### Scenario: No key
- **WHEN** no tiles key is set
- **THEN** no "Show on map" link is shown

### Requirement: The layout folds on smaller screens
Below 1024px wide the rail SHALL be closed behind a "Filters" button that opens it in place. Below 640px the header's four links SHALL show their icons alone, with their labels kept for screen readers, the search box SHALL take a row of its own, and a show's row SHALL stack: time and name, then venue, then price and save control. No public page SHALL scroll sideways at 390px wide.

#### Scenario: A phone
- **WHEN** the home page is opened 390px wide
- **THEN** the list is shown, "Filters" is a button, the four header links show as icons that a screen reader still names, the week strip scrolls within itself, and the page doesn't scroll sideways

#### Scenario: Opening the filters
- **WHEN** the visitor chooses "Filters" on a phone
- **THEN** the rail's controls are shown and work as they do at full width

### Requirement: The footer carries the links and credits
Every public page SHALL end with a footer holding the editors' footer links, "Privacy", "Terms" and the credit "© OpenStreetMap contributors" linking to OpenStreetMap's copyright page.

#### Scenario: The footer
- **WHEN** a visitor opens any public page
- **THEN** its footer links to `/privacy`, `/terms` and OpenStreetMap's copyright page

### Requirement: Keyboard and screen reader use
Every control in the header, the breadcrumbs, the rail, the week strip and the map link SHALL be reachable and operable from the keyboard, with a visible focus mark, and SHALL have a name a screen reader announces. Text and its ground SHALL meet a contrast ratio of 4.5 to 1, and 3 to 1 for text 24px and larger.

#### Scenario: Tabbing through the header
- **WHEN** a visitor tabs from the top of any page
- **THEN** focus moves through the name, the search box and the four links, each showing a focus mark

#### Scenario: Type on the accent
- **WHEN** a ticket price or the "Tonight" tag is drawn on the accent
- **THEN** its type meets 4.5 to 1
