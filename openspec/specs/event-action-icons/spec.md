# event-action-icons Specification

## Purpose

Gives each event in the listings a compact row of link icons (calendar file, Google Calendar, map, share and save), each named on hover. The row is built when the page is rendered, so it can change without re-rendering stored events.

## Requirements

### Requirement: Each event has a row of named link icons
Every event on the homepage, month archives, Saved shows page and search results SHALL show, in order:
- a calendar-file link to `/event/<id>/ics`, named "Download to your calendar (.ics)";
- a Google Calendar link to `/event/<id>/gcal`, named "Add to Google Calendar";
- when the event has a venue with a map location and no venue override, a map link to the venue's map, opening in a new tab, named "Map: <venue name>";
- a share link to `/event/<id>`, named "Share";
- the save bookmark (see `saved-shows`).

Each SHALL be an icon, with no visible text. Its name SHALL be its `title`: shown on hover, and, since the icon has no text, its accessible name for screen readers. The icons SHALL sit in a row of their own, below the event's text and above its play buttons, with no "+" separators.

#### Scenario: Icons with names
- **WHEN** an event at Paradise Rock Club is listed
- **THEN** its row has a calendar-file, Google Calendar, map, share and save icon, in that order, and the map icon's title is "Map: Paradise Rock Club"

#### Scenario: No map without a location
- **WHEN** an event's venue has no map location, or the event has a venue override
- **THEN** its row has no map icon

#### Scenario: Own row
- **WHEN** an event with play buttons is listed
- **THEN** the icon row comes after the event's text, and before the play buttons' row, and the text holds none of the links

#### Scenario: Search results
- **WHEN** a search lists an event
- **THEN** the event has the same icon row

### Requirement: The icon row is built with the page
The stored HTML of an event SHALL NOT contain the icon row, only a placeholder where it goes. The row SHALL be built each time a page is rendered, from the event's data and the visitor's request. Each icon's drawing SHALL be defined once per page and referenced by each row, rather than repeated in every row.

#### Scenario: Not in the stored HTML
- **WHEN** an event is saved
- **THEN** its stored HTML holds the placeholder, and none of the icon links

#### Scenario: Icons defined once
- **WHEN** the homepage lists several events
- **THEN** the page defines each icon once, and each event's row refers to the definitions
