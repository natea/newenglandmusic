## MODIFIED Requirements

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
