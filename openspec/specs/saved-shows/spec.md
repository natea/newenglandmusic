# saved-shows Specification

## Purpose

Lets a visitor mark the shows they're interested in, and see them all together, grouped by date, without making an account.

## Requirements

### Requirement: Visitors can save and unsave a show
Every event in the listings SHALL have a save bookmark, last in its row of link icons. It SHALL be outlined and named "Save show" when the show isn't saved, and filled and named "Saved (click to remove)" when it is. The name SHALL be its `title`, which is also its accessible name. The page SHALL render each bookmark's state from the visitor's `saved_shows` cookie.
- **With JavaScript:** clicking the bookmark SHALL save or unsave the show without reloading the page, and SHALL update every copy of the event on the page, including the day map's panel.
- **Without JavaScript:** clicking it SHALL post to `/saved/toggle/<id>`. That request SHALL update the cookie the same way, and redirect back to the page it came from, at the event.

Saved events SHALL be kept in a first-party cookie, `saved_shows`, holding their IDs, newest first. The cookie SHALL last a year, and be renewed on each change. The toggle SHALL ignore IDs of events that don't exist, and SHALL only redirect to a path on this site.

#### Scenario: Save a show
- **WHEN** a visitor clicks the bookmark on an event
- **THEN** the bookmark is filled, it's named "Saved (click to remove)", and the event's ID is in the `saved_shows` cookie

#### Scenario: Unsave a show
- **WHEN** a visitor clicks the bookmark on a saved event
- **THEN** the bookmark is outlined, it's named "Save show", and the event's ID is no longer in the cookie

#### Scenario: Saved state shown on load
- **WHEN** a visitor who saved an event opens any page listing it
- **THEN** that event's bookmark arrives filled from the server, and other events' arrive outlined

#### Scenario: Every copy of the event updates
- **WHEN** the day map's panel shows a copy of an event, and the visitor saves the event in the listing
- **THEN** the copy's bookmark is also filled

#### Scenario: No JavaScript
- **WHEN** JavaScript is off and a visitor clicks an event's bookmark on the homepage
- **THEN** the browser posts to `/saved/toggle/<id>`, the cookie gains the event's ID, and the visitor is returned to the homepage at that event, with its bookmark filled

#### Scenario: Toggle rejects other sites and unknown events
- **WHEN** a toggle request names an event that doesn't exist, or a `next` address on another site
- **THEN** the cookie doesn't gain the ID, and the redirect goes to a page on this site

### Requirement: The Saved shows page lists upcoming saved shows by date
`/saved` SHALL list the visitor's saved events that are approved and haven't started yet, in start-time order, grouped under the same date headings as the homepage. Each event SHALL look exactly as it does in the listing, play buttons and icon row, save bookmark included.

The page SHALL ignore the region, state and metro filter, and SHALL NOT change the remembered filter. With no upcoming saved shows, it SHALL say so, and explain how to save one.

The page SHALL accept a `group` parameter, so that other groupings can be added later. `date` is the only value, and the default; any other value SHALL be treated as `date`.

#### Scenario: Grouped by date
- **WHEN** a visitor has saved two shows on Nov 6 and one on Nov 8
- **THEN** `/saved` shows a Nov 6 heading with two events in start-time order, then a Nov 8 heading with one

#### Scenario: Area filter ignored
- **WHEN** a visitor's remembered filter is Vermont, and they saved a show in Maine
- **THEN** `/saved` lists the Maine show, and the remembered filter is still Vermont

#### Scenario: Nothing saved
- **WHEN** the visitor has no saved shows, or none upcoming
- **THEN** `/saved` says there are no saved shows, and explains the save bookmark

#### Scenario: Unknown group
- **WHEN** a visitor opens `/saved?group=venue`
- **THEN** the shows are grouped by date

### Requirement: Shows that can no longer happen drop off
On `/saved`, the site SHALL leave out saved IDs for events that are past, deleted or unapproved, and SHALL rewrite the cookie without them. IDs that aren't positive whole numbers SHALL be ignored and dropped. The cookie SHALL hold at most 300 IDs; saving beyond that SHALL drop the oldest saved.

#### Scenario: Past show dropped
- **WHEN** a saved show's start time has passed
- **THEN** it isn't listed on `/saved`, and the response's cookie no longer holds its ID

#### Scenario: Deleted or unapproved show dropped
- **WHEN** a saved event has been deleted, or marked unapproved
- **THEN** it isn't listed, and its ID is dropped from the cookie

#### Scenario: Malformed cookie
- **WHEN** the cookie holds "12,abc,,-3,12"
- **THEN** the page treats it as the single ID 12, and rewrites the cookie as "12"

#### Scenario: Limit
- **WHEN** a visitor with 300 saved shows saves another
- **THEN** the new one is kept, and the oldest saved is dropped

### Requirement: The header shows a Saved shows link with a count
Every page's header SHALL have a "Saved shows" link to `/saved`. When JavaScript is on and the visitor has saved shows, the link SHALL show their number, for example "Saved shows (3)", and SHALL update as shows are saved and unsaved. The count SHALL be of the IDs in the cookie, so it can briefly include shows the Saved shows page will drop.

#### Scenario: Count shown
- **WHEN** a visitor has saved three shows
- **THEN** the header link reads "Saved shows (3)"

#### Scenario: Count updates
- **WHEN** the visitor saves a fourth show
- **THEN** the header link reads "Saved shows (4)" without a reload

#### Scenario: Nothing saved
- **WHEN** the visitor has saved nothing
- **THEN** the header link reads "Saved shows", with no number

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
