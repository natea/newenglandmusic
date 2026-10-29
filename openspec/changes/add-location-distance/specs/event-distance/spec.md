## Purpose

Lets a visitor see how far each show is from them: from a ZIP code or town they type, or from their device's position. The events stay in time order, and each one shows a "(0.5 mi away)" label.

## ADDED Requirements

### Requirement: ZIP codes and towns are looked up in Census Gazetteer data
`load_census_gazetteer [--year 2026]` SHALL download the Census Bureau's Gazetteer files for ZIP Code Tabulation Areas, county subdivisions and places for that year, and replace the lookup table with their names and internal points. A name's Census suffix ("city", "town", "CDP", "village", "borough", "township" and the like) SHALL be dropped, so "Somerville city" is stored as "Somerville". A county subdivision and a place with the same name in the same state SHALL be stored once. When a download fails, the existing table SHALL be left as it was. The command SHALL print how many ZIP areas and towns it loaded.

A visitor's text SHALL be looked up as:
- **five digits:** a ZIP area by its code;
- **"<town>, <state>":** a town by its name and state, where the state is a two-letter code or a full name, ignoring case, accents and punctuation;
- **"<town>":** a town by its name. When exactly one of the matching towns has a venue on the site, it SHALL be chosen. Otherwise towns in states where the site has venues SHALL be preferred, and when several such towns match, the visitor SHALL be offered them to choose from.

#### Scenario: ZIP code
- **WHEN** a visitor enters "02144"
- **THEN** the location is ZIP 02144's internal point, labelled "02144"

#### Scenario: Town and state
- **WHEN** a visitor enters "somerville, ma"
- **THEN** the location is Somerville, MA's internal point, labelled "Somerville, MA"

#### Scenario: Town name only
- **WHEN** a visitor enters "Hamden", and the only Hamdens are in CT and NY, where the site has venues in CT only
- **THEN** the location is Hamden, CT

#### Scenario: The town with venues
- **WHEN** a visitor enters "Somerville", which is in MA, ME and NJ, where the site has venues in all three states but only Somerville, MA has one itself
- **THEN** the location is Somerville, MA

#### Scenario: Several towns with the name
- **WHEN** a visitor enters "Springfield", and the site has venues in MA, VT and NJ, which each have a Springfield
- **THEN** no location is set, and the visitor is offered "Springfield, MA", "Springfield, VT" and "Springfield, NJ" to choose from

#### Scenario: Not found
- **WHEN** a visitor enters "99999" or "Xyzzyville"
- **THEN** no location is set, and the page says the place wasn't found and suggests a town name or another ZIP code

#### Scenario: Loading the data
- **WHEN** `load_census_gazetteer --year 2026` runs with the Census files available
- **THEN** the table holds their ZIP areas and towns, with "Somerville city, MA" stored as "Somerville", MA, and the old rows are gone

#### Scenario: Download fails
- **WHEN** a Census file can't be downloaded
- **THEN** the command fails with a message, and the table is unchanged

### Requirement: The location field suggests towns as you type
With JavaScript, typing two or more characters in the location field SHALL suggest up to eight places from the Census table, in the browser's own suggestion list. They're shown as "<town>, <state>", or as a ZIP code when the text is digits. A suggestion SHALL be chosen by the same rules as a typed place, so choosing one sets that exact place. The suggestions SHALL come from `/location/suggest?q=…`, which returns them as JSON:
- towns whose name starts with the text;
- towns with venues on the site first, then towns in states where the site has venues, then the rest, alphabetically within each;
- for digits, ZIP codes starting with them.

Without JavaScript, the field SHALL work as a plain text field.

#### Scenario: Suggestions while typing
- **WHEN** a visitor types "som"
- **THEN** "Somerville, MA" is suggested first, as the town with venues, followed by other Somervilles and towns starting with "Som", at most eight

#### Scenario: ZIP prefix
- **WHEN** a visitor types "0214"
- **THEN** ZIP codes starting with 0214 are suggested, such as "02144"

#### Scenario: Too short
- **WHEN** a visitor has typed one character
- **THEN** nothing is suggested

### Requirement: Visitors can set and clear their location
The listing, month archive and saved shows pages SHALL offer a location form: a text field for a ZIP code or town, and a "Use my location" button. The form SHALL work without JavaScript for typed places. "Use my location" SHALL need JavaScript. It SHALL ask the browser for the device's position only when pressed, and send it rounded to three decimal places (about 100 m).

Setting a location SHALL store it in a first-party cookie for one year: its label and its coordinates rounded to three decimal places. The site SHALL NOT store the location anywhere else. A "clear" link SHALL delete the cookie. A browser that refuses or can't give a position SHALL leave the location as it was, with a message. After setting or clearing, the visitor SHALL return to the page they came from.

#### Scenario: Typed location
- **WHEN** a visitor enters "02144" on the homepage
- **THEN** they return to the homepage, which shows the location as "02144" with a "clear" link, and the cookie holds it

#### Scenario: Device location
- **WHEN** a visitor presses "Use my location" and allows it, at 42.39613, -71.12212
- **THEN** the location is set to 42.396, -71.122, labelled "your location"

#### Scenario: Position refused
- **WHEN** a visitor presses "Use my location" and refuses
- **THEN** the location is unchanged, and the page says the position wasn't available

#### Scenario: Clearing
- **WHEN** a visitor follows "clear"
- **THEN** the cookie is deleted, and events show no distances

#### Scenario: Not stored on the server
- **WHEN** a visitor sets a location
- **THEN** no database row holds it

### Requirement: Events show how far they are from the visitor's location
When a location is set, each event whose venue has coordinates SHALL show its straight-line distance from the location in miles, as "(0.5 mi away)", next to its icon row. This SHALL apply on the listing, the month archives, the saved shows page and the map panels. Distances under 10 miles SHALL show one decimal place, and others whole miles. Under 0.1 miles SHALL show "(less than 0.1 mi away)". Events SHALL stay in time order. An event at a venue override, or at a venue without coordinates, SHALL show no distance. With no location set, no distance SHALL show, and pages SHALL be as they are now. The stored event HTML SHALL NOT contain distances, which are added when a page is rendered.

#### Scenario: Distances shown
- **WHEN** a visitor's location is 02144, and an event is at a venue 0.47 miles from its point
- **THEN** the event shows "(0.5 mi away)", and the events are still listed by time

#### Scenario: Far away
- **WHEN** an event's venue is 143.6 miles from the location
- **THEN** it shows "(144 mi away)"

#### Scenario: No coordinates
- **WHEN** an event has a venue override, or its venue has no coordinates
- **THEN** it shows no distance

#### Scenario: No location
- **WHEN** a visitor has no location set
- **THEN** no event shows a distance

#### Scenario: Stored HTML unchanged
- **WHEN** an event is re-saved
- **THEN** its stored HTML holds no distance, whatever any visitor's location
