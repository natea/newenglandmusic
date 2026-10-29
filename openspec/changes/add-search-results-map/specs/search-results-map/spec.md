## Purpose

Lets a visitor see where the shows matching their search are, on one map, as they can for a day's shows or their saved shows.

## ADDED Requirements

### Requirement: The search results page has a map of the upcoming results
When a Protomaps key is set and at least one upcoming search result is at a venue with a map location, the search results page SHALL show a "SHOW MAP" toggle above its results. A result SHALL be upcoming when it starts today or later, in New York time.
- **Opening it** SHALL show one map, with a pin for every upcoming result at a located venue, fitted to show all the pins.
- **Past results** SHALL stay in the list, in its current order, and SHALL get no pin.
- **Labels and pins** SHALL work as on the Saved shows map: each pin labelled with its shows' dates and start times, venues within about 50 metres sharing a pin, and clicking a pin listing its shows below the map, with their icon rows.
- **Closing it:** the toggle SHALL then read "HIDE MAP", and clicking it again SHALL hide the map and the list below it.

Cancelled results, and results whose venue has no map location or that have a venue override, SHALL get no pin. When no upcoming result can be mapped, or no Protomaps key is set, no toggle SHALL be shown. The map SHALL NOT load until the visitor opens it. The listing's day maps and the Saved shows map SHALL behave as before.

#### Scenario: Map of upcoming results
- **WHEN** a search for "beehive" finds two upcoming shows at The Beehive and three past ones there
- **THEN** the map has one pin, at The Beehive, labelled with the two upcoming shows' dates and times, and the three past shows are still listed

#### Scenario: Results at several venues
- **WHEN** a search finds upcoming shows at Paradise Rock Club and at Higher Ground
- **THEN** the map has two pins, and fits both

#### Scenario: Clicking a pin
- **WHEN** the visitor clicks a pin
- **THEN** that pin's upcoming shows are listed below the map, with their icon rows, and no past show is among them

#### Scenario: Only past results
- **WHEN** every result of a search is in the past
- **THEN** no map toggle is shown

#### Scenario: Not loaded until opened
- **WHEN** a search results page loads with upcoming located results
- **THEN** no map is created and no map tiles are requested until the visitor clicks "SHOW MAP"

#### Scenario: Other maps unchanged
- **WHEN** a visitor opens a day's map on the listing, or the Saved shows map
- **THEN** they show the same pins as before
