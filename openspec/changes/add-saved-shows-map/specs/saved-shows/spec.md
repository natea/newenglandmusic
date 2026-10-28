## ADDED Requirements

### Requirement: The Saved shows page has a map of the saved shows
When a Protomaps key is set and at least one listed saved show is at a venue with a map location, `/saved` SHALL show a "SHOW MAP" toggle above its list.
- **Opening it** SHALL show one map, with a pin for every listed saved show at a located venue, fitted to show all the pins.
- **Sharing a pin:** shows at the same venue, or at venues within about 50 metres of each other (next-door rooms, whose pins would otherwise hide each other), SHALL share a pin.
- **Labels:** each pin's label SHALL give each of its shows on a line of its own: its date and start time, such as "Nov 6 7:00pm", then the start of its name.
- **Clicking a pin** SHALL list its shows below the map, as they appear in the list, each with its day and date above its time, on lines of their own ("Thu", "Oct 29", "7:00pm"), so its text lines up with the list's.
- **Closing it:** the toggle SHALL then read "HIDE MAP", and clicking it again SHALL hide the map and the list below it.

Cancelled shows, and shows whose venue has no map location, SHALL get no pin, but SHALL stay in the page's list. A show pinned on the day maps SHALL be pinned the same way here. When no listed saved show can be mapped, or no Protomaps key is set, no toggle SHALL be shown. The map SHALL NOT load until the visitor opens it. The listing's day maps SHALL behave as before, except that they too SHALL merge venues within about 50 metres into one pin.

#### Scenario: Map of saved shows over several days
- **WHEN** a visitor has saved a show at Paradise Rock Club on Nov 6 and one at Higher Ground on Nov 8, and opens the map
- **THEN** the map has two pins, labelled with "Nov 6" and "Nov 8" and each show's time, and fits both

#### Scenario: Shows at one venue share a pin
- **WHEN** two saved shows are at the same venue on different days
- **THEN** they share one pin, whose label lists both dates and times

#### Scenario: Next-door venues share a pin
- **WHEN** one saved show is at The Atlantis on Oct 29 and another at the 9:30 Club, 28 metres away, on Nov 15
- **THEN** they share one pin, labelled "Oct 29 6:30pm Dana and Alden…" and "Nov 15 7:00pm Giant Rooks" on lines of their own, and clicking it lists both

#### Scenario: Venues a street apart keep their own pins
- **WHEN** two saved shows are at venues about 100 metres apart
- **THEN** each has its own pin

#### Scenario: Clicking a pin
- **WHEN** the visitor clicks a pin
- **THEN** that pin's shows are listed below the map, with their icon rows, and each shows its day and date (such as "Thu Oct 29") above its time

#### Scenario: Shows that can't be mapped
- **WHEN** a saved show's venue has no map location, or it has no venue, or it's cancelled
- **THEN** it gets no pin, and is still in the list

#### Scenario: Nothing to map
- **WHEN** none of the visitor's listed saved shows can be mapped, or the site has no Protomaps key
- **THEN** `/saved` shows no map toggle

#### Scenario: Not loaded until opened
- **WHEN** `/saved` loads with mappable saved shows
- **THEN** no map is created and no map tiles are requested until the visitor clicks "SHOW MAP"

#### Scenario: Day maps unchanged
- **WHEN** a visitor opens a day's map on the listing
- **THEN** it shows only that day's shows, labelled with their times, as before
