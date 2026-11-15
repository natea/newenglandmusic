## ADDED Requirements

### Requirement: Public pages show only New England events
The public site SHALL list an event only when its venue's state is Massachusetts, Connecticut, Rhode Island, New Hampshire, Maine or Vermont. Events at venues in other states, and events with no linked venue, SHALL NOT appear in the homepage and month listings (including the calendar's event dates and day maps) or in site search results.

#### Scenario: Listing hides a New York show
- **WHEN** an approved event at a venue in New York is on today's date and a visitor opens `/`
- **THEN** the event isn't listed, and an approved event at a Massachusetts venue on the same date is

#### Scenario: Search hides a New Jersey show
- **WHEN** a visitor searches for the title of an approved event at a venue in New Jersey
- **THEN** the results don't include the event

### Requirement: Other public surfaces follow the same scope
The calendar feeds, the saved shows page, act and band pages' show lists and next-show dates, the A–Z act index, search suggestions, the discover page and the months the sitemap lists SHALL include only events that the listings would show. Hiding applies to lists: an event opened by its own link still opens.

#### Scenario: Calendar feed outside New England
- **WHEN** a visitor requests `/calendar.ics` with no filter
- **THEN** it contains the New England events and none from other states

#### Scenario: Act page
- **WHEN** an act has one upcoming show in Vermont and one in Pennsylvania
- **THEN** its page lists only the Vermont show

#### Scenario: Event without a linked venue
- **WHEN** an approved event has no linked venue
- **THEN** it doesn't appear in the listings or search

#### Scenario: Next-show dates
- **WHEN** an act's only upcoming show is at a New York venue
- **THEN** the A–Z index and the act suggestions show no next-show date for it

#### Scenario: Saved shows
- **WHEN** a visitor has saved an event at a Pennsylvania venue and opens the saved shows page
- **THEN** the event isn't listed

#### Scenario: Search suggestions
- **WHEN** a visitor types the title of an approved New Jersey event in the search box
- **THEN** the suggestions don't include the event

#### Scenario: Discover
- **WHEN** the only upcoming shows of an act are outside New England
- **THEN** the discover page shows no card for that act

#### Scenario: Sitemap months
- **WHEN** the only events in a month are at venues outside New England
- **THEN** that month isn't in the sitemap

### Requirement: Nothing is deleted and the pipeline is unchanged
The admin SHALL keep showing all events, no venue or event SHALL be deleted, and event fetching SHALL keep saving events for every venue.

#### Scenario: Admin and data untouched
- **WHEN** an editor opens the event list in the admin
- **THEN** events at venues outside New England are still listed, and no event or venue was deleted

#### Scenario: Artist matching unchanged
- **WHEN** an artist is named only by an approved event at a New York venue and `match_spotify_artists` runs
- **THEN** the artist is still matched, as before

#### Scenario: Fetching continues
- **WHEN** `fetch_events` runs for a venue outside New England
- **THEN** its new events are still saved, unapproved, as before

### Requirement: The New England states are one setting
The states counted as New England SHALL be defined in one place, so a later phase can widen the site's scope by changing that list alone.

#### Scenario: Widening the list
- **WHEN** the list of states gains New York
- **THEN** approved events at New York venues appear in the listings and New York is offered as a State option, with no other change

### Requirement: Removed areas in links and cookies are ignored
A URL or remembered filter naming an area that the site no longer offers SHALL be treated as an unknown area: it filters nothing and sets no cookie.

#### Scenario: Old link to New York
- **WHEN** a visitor opens `/?state=new-york`
- **THEN** the page shows the unfiltered New England listing, with no State selected

#### Scenario: Old feed subscription
- **WHEN** a calendar app fetches `/calendar.ics?state=new-york`
- **THEN** the feed holds the unfiltered New England events

#### Scenario: Old cookie
- **WHEN** a visitor's remembered filter names only the Mid-Atlantic region and they open `/`
- **THEN** the cookie is cleared and the unfiltered New England listing is shown
