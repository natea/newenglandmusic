# Spec Delta

## Purpose
Describes what every public page shares: the header with the site's name, the search and location bar and the main links; breadcrumbs; the footer; and the filter rail and map panel that listing pages are built from, including how they fold on smaller screens.

## ADDED Requirements

### Requirement: Every page has the same header
Every public page SHALL open with a header holding, in this order: the site's name linking to the home page; one bar holding the search box and the visitor's location, with a search button; and links to "Submit a show", "Saved", "Venues" and "Bands", each with an icon. The header SHALL have no menu that must be opened to reach those links at 1024px wide and up.

#### Scenario: The header's parts
- **WHEN** a visitor opens the home page, a venue's page or the privacy page 1440px wide
- **THEN** each shows the name, the search and location bar, and the four links, in that order

#### Scenario: The links go where they say
- **WHEN** the visitor follows "Submit a show", "Saved", "Venues" and "Bands"
- **THEN** they open `/submit-event`, `/saved`, `/venues` and `/bands`

### Requirement: The header shows and sets the visitor's location
The bar SHALL show the visitor's saved location beside the search box, or "Set your location" when none is saved. Choosing it SHALL open the site's location form, with its suggestions, without leaving the page; saving a location there SHALL return the visitor to the page they were on. Without JavaScript it SHALL link to the location form's own page.

#### Scenario: A saved location
- **WHEN** a visitor whose saved location is Medford, MA opens any page
- **THEN** the bar reads "Medford, MA"

#### Scenario: No location
- **WHEN** a visitor with no saved location opens any page
- **THEN** the bar reads "Set your location"

#### Scenario: Setting it from the header
- **WHEN** the visitor chooses the location in the bar on `/venues`, picks "Salem, MA" and saves
- **THEN** they're back on `/venues` and the bar reads "Salem, MA"

### Requirement: Pages below the home page have breadcrumbs
Every public page other than the home page SHALL show, under the header, the path from the home page to itself: each step before the last as a link, the page itself last and not a link. A venue's page SHALL pass through "Venues" and, when the venue has a neighborhood or town, that place; a band's or artist's page through "Bands & artists"; a show's page through its venue.

#### Scenario: A venue's page
- **WHEN** a visitor opens the page of O'Brien's, in Allston
- **THEN** the breadcrumbs read "Home / Venues / Allston / O'Brien's", the first three as links

#### Scenario: A band's page
- **WHEN** a visitor opens Horse Jumper of Love's page
- **THEN** the breadcrumbs read "Home / Bands & artists / Horse Jumper of Love"

#### Scenario: The home page
- **WHEN** a visitor opens the home page with no filter
- **THEN** no breadcrumbs are shown

### Requirement: The listing's heading says where it covers
The home page's heading SHALL name what the listing covers: "Live music near <location>" when the visitor has a saved location, "Live music in <area>" when only an area filter is set, naming the narrowest area chosen, and "Live music across New England" otherwise.

#### Scenario: Near a location
- **WHEN** a visitor whose location is Medford, MA opens the home page
- **THEN** the heading reads "Live music near Medford, MA"

#### Scenario: In an area
- **WHEN** a visitor with no location filters to the Greater Boston metro area
- **THEN** the heading reads "Live music in Greater Boston"

#### Scenario: Neither
- **WHEN** a visitor with no location and no filter opens the home page
- **THEN** the heading reads "Live music across New England"

### Requirement: Listing pages have a filter rail
The home page, the venues listing and the bands listing SHALL show their filters in a rail beside the list, headed "Filters", each group of choices under its own label. The rail SHALL hold every filter that page already offers and no control that does nothing.

#### Scenario: The venues listing's filters
- **WHEN** a visitor opens `/venues` 1440px wide
- **THEN** the rail holds the place filters, the genre choice and "Takes open bookings", and choosing one filters the list as it did before

#### Scenario: No dead controls
- **WHEN** any listing page is opened
- **THEN** every control in its rail changes what the list shows

### Requirement: Listing pages show their map beside the list
When a map tiles key is set, the home page and the venues listing SHALL show a map of what's listed in a panel beside the list at 1024px wide and up, open without a click, that stays in view as the list scrolls. Choosing a pin SHALL show what it stands for, with a link to it. Without a tiles key no panel SHALL be drawn and the list SHALL take the width.

#### Scenario: The map is open
- **WHEN** a visitor opens the home page 1440px wide with a tiles key set and located shows listed
- **THEN** the map is shown beside the list, with a pin for each located venue listed

#### Scenario: A pin
- **WHEN** the visitor chooses the pin at O'Brien's
- **THEN** a callout names the show there and its time, linking to it

#### Scenario: No key
- **WHEN** no tiles key is set
- **THEN** no map panel is drawn and the list fills the page's width

### Requirement: The layout folds on smaller screens
Below 1024px wide the map panel SHALL be closed behind a "Map" button and the filter rail behind a "Filters" button, each opening in place. Below 640px the header's four links SHALL show their icons with their names kept for screen readers, and the search and location bar SHALL take a row of its own. No public page SHALL scroll sideways at 390px wide.

#### Scenario: A phone
- **WHEN** the home page is opened 390px wide
- **THEN** the list is shown, "Filters" and "Map" are buttons, nothing scrolls sideways, and each header link still has its name for a screen reader

#### Scenario: Opening the filters
- **WHEN** the visitor chooses "Filters" on a phone
- **THEN** the filters are shown and work as they do in the rail

### Requirement: The footer carries the links and credits
Every public page SHALL end with a footer holding the editors' footer links, "Privacy", "Terms" and the credit "© OpenStreetMap contributors" linking to OpenStreetMap's copyright page.

#### Scenario: The footer
- **WHEN** a visitor opens any public page
- **THEN** its footer links to `/privacy`, `/terms` and OpenStreetMap's copyright page

### Requirement: Keyboard and screen reader use
Every control in the header, the breadcrumbs, the filter rail and the map panel's buttons SHALL be reachable and operable from the keyboard, with a visible focus mark, and SHALL have a name a screen reader announces. Text and its ground SHALL meet a contrast ratio of 4.5 to 1, and 3 to 1 for text 24px and larger.

#### Scenario: Tabbing through the header
- **WHEN** a visitor tabs from the top of any page
- **THEN** focus moves through the name, the search box, the location, the search button and the four links, each showing a focus mark

#### Scenario: Type on the accent
- **WHEN** the "Tonight" tag is drawn
- **THEN** its type on the accent meets 4.5 to 1
