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

### Requirement: Nothing is deleted, and the admin opens on New England
No venue or event SHALL be deleted. The admin's event list, its all-events review queue and its venue list SHALL show New England's events and venues by default, and SHALL offer an "All areas" choice that shows every one. A Region, State or Metro filter chosen in the admin SHALL show that area's events or venues wherever it is, without the default narrowing them.

#### Scenario: Admin opens on New England
- **WHEN** an editor opens the all-events review queue with no filter chosen
- **THEN** only events at New England venues are listed, and an unapproved event at a New York venue isn't

#### Scenario: All areas
- **WHEN** the editor chooses "All areas"
- **THEN** events at venues everywhere are listed, the New York one included

#### Scenario: A chosen state outside New England
- **WHEN** the editor chooses the State filter "New York" in the venue list
- **THEN** New York's venues are listed

#### Scenario: Nothing deleted
- **WHEN** the scope applies
- **THEN** no event or venue was deleted

#### Scenario: Artist matching unchanged
- **WHEN** an artist is named only by an approved event at a New York venue and `match_spotify_artists` runs
- **THEN** the artist is still matched, as before

### Requirement: Events are fetched only for New England venues
`fetch_events` SHALL fetch events only for venues in New England and venues with no state, unless `--sheet-ids` names a venue, which is fetched wherever it is. Existing events at other venues SHALL be left as they are.

#### Scenario: A venue outside New England is skipped
- **WHEN** `fetch_events --all` runs and a New York venue has a saved event source
- **THEN** no events are fetched for it, and its existing events are left as they are

#### Scenario: A venue with no state is fetched
- **WHEN** `fetch_events --all` runs for a venue whose state is blank
- **THEN** its events are fetched as before

#### Scenario: Named on purpose
- **WHEN** `fetch_events --sheet-ids` names a New York venue
- **THEN** its events are fetched

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
