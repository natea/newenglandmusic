# Spec Delta

## MODIFIED Requirements

### Requirement: Each event has a row of named link icons
Every event on the homepage, month archives, Saved shows page and search results SHALL show, in order:
- a calendar-file link to `/event/<id>/ics`, named "Download to your calendar (.ics)";
- a Google Calendar link to `/event/<id>/gcal`, named "Add to Google Calendar";
- when the event has a venue with a map location and no venue override, a map link to the venue's map, opening in a new tab, named "Map: <venue name>";
- a share link to `/event/<id>`, named "Share".

Each SHALL be an icon, with no visible text. Its name SHALL be its `title`: shown on hover, and, since the icon has no text, its accessible name for screen readers. The icons SHALL sit in a row of their own, below the event's text and above its play buttons, with no "+" separators. The save bookmark (see `saved-shows`) SHALL sit apart from them, at the end of the event's row, after its price.

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

#### Scenario: The bookmark at the row's end
- **WHEN** an event is listed on the homepage
- **THEN** its save bookmark is at the end of its row, after the price, and the four link icons are in their own row under the event's text
