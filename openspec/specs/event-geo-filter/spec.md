# event-geo-filter Specification

## Purpose
Lets visitors and admins narrow the events listing, and the admin event and venue lists, to one region, state or metro area. These are the areas the venue sheet defines, so the site browses the same geography as the Music Map.

## Requirements

### Requirement: A venue belongs to an area by the sheet's rules
Each region, state and metro area SHALL have the matching rules the sheet gives it: a list of states, plus optional lists of counties and cities. A venue SHALL belong to an area when its state is in the area's states and either:
- the area has no county or city lists, or
- the venue's county is in the county list, or its city is in the city list.

Comparisons SHALL ignore case and surrounding whitespace. A venue MAY belong to several areas at once. Events SHALL belong to the areas of their linked venue, and an event with no linked venue SHALL belong to no area.

#### Scenario: State-only region
- **WHEN** the region "New England: South" lists the states CT, MA and RI
- **THEN** every venue in CT, MA or RI belongs to it, and no venue in NH does

#### Scenario: Metro matched by county
- **WHEN** the metro "MA: Cape Cod" lists the state MA and the counties Barnstable, Dukes and Nantucket
- **THEN** a MA venue in Barnstable county belongs to it, and a MA venue in Suffolk county does not

#### Scenario: Metro matched by county or city
- **WHEN** the metro "MA: Boston" lists the state MA, the county Suffolk and the cities Brookline, Cambridge and Somerville
- **THEN** a MA venue in Suffolk county belongs to it, and so does a MA venue in Middlesex county whose city is Cambridge

#### Scenario: Same county name in another state
- **WHEN** a venue is in Middlesex county, CT, and the metro "MA: Central" lists the state MA only
- **THEN** the venue doesn't belong to "MA: Central"

#### Scenario: Nested metros
- **WHEN** a venue is in Cambridge, MA
- **THEN** it belongs to both "MA: Boston" and "MA: Boston Metro Region"

#### Scenario: Event without a venue
- **WHEN** an event has no linked venue
- **THEN** it doesn't match any region, state or metro filter

### Requirement: Only areas that can match appear as options
The site and the admin SHALL offer as options only areas whose rules list at least one state. Options SHALL appear in the sheet's row order. Each area SHALL have a URL value made from its label; for metro areas, the value SHALL include the state, so that two states' "North" metros don't clash.

#### Scenario: Area with no states
- **WHEN** the sheet lists the region "Northeast Corridor" with no states
- **THEN** "Northeast Corridor" isn't offered on the site or in the admin

#### Scenario: Sheet order
- **WHEN** the sheet lists the regions Chesapeake Bay, Mid-Atlantic and New England, in that order
- **THEN** the Region options appear in that order

### Requirement: Visitors can filter the events listing by region, state and metro area
The homepage and the month archive pages SHALL offer Region, State and Metro Area filters. They SHALL be chosen with the `region`, `state` and `metro` URL query parameters and SHALL work without JavaScript. When a filter is set, the event list, the calendar's event dates and the day maps SHALL include only events that belong to the chosen areas. Filters given together SHALL all apply. With no filter set, the page SHALL show what it shows today.

#### Scenario: Filter by state
- **WHEN** a visitor opens `/?state=vermont`
- **THEN** only events at Vermont venues are listed, and the State filter shows Vermont as selected

#### Scenario: Filter by metro area
- **WHEN** a visitor opens `/?metro=ny-hudson-valley`
- **THEN** only events at venues in the Hudson Valley counties are listed

#### Scenario: Region and state together
- **WHEN** a visitor opens `/?region=new-england&state=new-york`
- **THEN** no events are listed, and the page says that no events match the filters and links to the unfiltered listing

#### Scenario: Month archive
- **WHEN** a visitor opens `/2026-11/?region=new-england-north`
- **THEN** only November events at venues in ME, NH or VT are listed

#### Scenario: No filter
- **WHEN** a visitor with no remembered filter opens `/` with no filter parameters
- **THEN** events from every venue are listed, as they are today

### Requirement: The metro area options follow the chosen state
When a state is chosen, the Metro Area options SHALL list only that state's metros. With no state chosen, the options SHALL list every metro, grouped by state. A metro that belongs to a different state from the chosen state SHALL be ignored. A state with no metros SHALL show no Metro Area options.

#### Scenario: Metros narrowed to the state
- **WHEN** a visitor has chosen Massachusetts
- **THEN** the Metro Area options are the Massachusetts metros, such as Berkshires, Boston Metro Region and Cape Cod, and no metros from other states

#### Scenario: Metro from another state
- **WHEN** a visitor opens `/?state=massachusetts&metro=ny-hudson-valley`
- **THEN** the listing shows all Massachusetts events, and no metro is selected

#### Scenario: State without metros
- **WHEN** a visitor has chosen Rhode Island
- **THEN** no metro options are offered

### Requirement: Filters survive navigation and bad input
The previous, current and next month links SHALL keep the chosen filters. An unknown or stale filter value SHALL be ignored, as though it wasn't given, and SHALL NOT cause an error page.

#### Scenario: Month links keep the filter
- **WHEN** a visitor on `/?state=maine` follows the next-month link
- **THEN** the next month's archive opens with `state=maine` still applied

#### Scenario: Unknown value
- **WHEN** a visitor opens `/?state=atlantis`
- **THEN** the page returns 200 and lists events from every venue

### Requirement: The site remembers a visitor's last filter
The site SHALL remember a visitor's last filter in a first-party cookie, so that a later visit opens with the same filter applied.
- **Setting the cookie:** when a listing page is opened with at least one valid filter, the response SHALL save the resolved filter in the cookie. The cookie SHALL expire after one year.
- **Using the cookie:** when the homepage or a month archive is opened with no `region`, `state`, `metro` or `clear` parameter and the cookie holds a valid filter, the response SHALL redirect to the same page with that filter's parameters.
- **Clearing the cookie:** opening a listing page with `clear` set, or with the filter parameters present but all empty, SHALL delete the cookie and show the unfiltered listing.
- **Stale values:** a cookie whose values no longer match any offered area SHALL be deleted, without a redirect.
- **Other pages:** the cookie SHALL NOT affect search results or any other page.

#### Scenario: Filter is remembered
- **WHEN** a visitor opens `/?state=vermont` and later opens `/`
- **THEN** the second request redirects to `/?state=vermont`

#### Scenario: Remembered filter on a month archive
- **WHEN** a visitor whose cookie holds `state=vermont` opens `/2026-11/`
- **THEN** the request redirects to `/2026-11/?state=vermont`

#### Scenario: A shared link wins over the cookie
- **WHEN** a visitor whose cookie holds `state=vermont` opens `/?state=maine`
- **THEN** Maine events are listed, and the cookie now holds `state=maine`

#### Scenario: Clearing the filter
- **WHEN** a visitor with a remembered filter sets every filter to "All", or follows the "show all" link
- **THEN** the unfiltered listing is shown, the cookie is deleted, and a later visit to `/` isn't redirected

#### Scenario: Stale cookie
- **WHEN** a visitor's cookie holds the slug of a metro that has since been removed from the sheet
- **THEN** `/` shows the unfiltered listing with no redirect, and the cookie is deleted

#### Scenario: No filter chosen
- **WHEN** a visitor who has never chosen a filter opens `/`
- **THEN** no cookie is set and the page isn't redirected

#### Scenario: Search ignores the cookie
- **WHEN** a visitor with a remembered filter searches with `/?s=jazz`
- **THEN** the search results aren't filtered and the request isn't redirected

### Requirement: Admins can filter events and venues by region, state and metro area
The admin's event list and all-events list (`/admin/core/alleventproxy/`) SHALL have Region, State and Metro Area sidebar filters that use the same areas and membership rules as the site. The venue list SHALL have the same three filters. They SHALL combine with the existing admin filters. When a state is chosen, the Metro Area filter SHALL list only that state's metros.

#### Scenario: Review queue for one metro
- **WHEN** an admin filters the all-events list to the metro "MA: Boston Metro Region" and to unapproved events
- **THEN** only unapproved events at venues in that metro are listed

#### Scenario: Venues by region
- **WHEN** an admin filters the venue list to the region "Tri-State"
- **THEN** only venues in CT, NJ or NY are listed

#### Scenario: Admin metro list follows the state
- **WHEN** an admin has chosen the State filter "Vermont"
- **THEN** the Metro Area filter lists only "VT: North" and "VT: South"

### Requirement: Visitors can narrow a metro area to some of its towns
Once a metro area is chosen, the filter SHALL offer the towns in it that have at least one venue, by the venues' town and state, in alphabetical order, as a multi-select. The `town` URL parameter SHALL name a chosen town as "<town>, <state code>", such as `town=Somerville, MA`, and MAY be repeated. When towns are chosen, the listing, the calendar's event dates, the day maps and the calendar feeds SHALL include only events at venues in those towns. A town outside the chosen metro, or unknown, SHALL be ignored. Choosing no town SHALL mean the whole metro. Without a metro, `town` SHALL be ignored. The chosen towns SHALL be kept in the remembered filter, and in the month links, like the other filters. The multi-select SHALL work without JavaScript. Changing the metro SHALL drop towns that aren't in the new one.

With JavaScript, the multi-select SHALL be shown as an "add a town" list beside the chosen towns. Each chosen town SHALL be shown as a chip with a button to remove it. Choosing a town from the list SHALL add it, and removing one SHALL drop it. Either SHALL apply the filter at once. Towns already chosen SHALL NOT be offered again in the list.

#### Scenario: Adding and removing towns
- **WHEN** a visitor with the Boston Metro Region chosen picks Somerville, then Cambridge, from "add a town", then removes Somerville with its ×
- **THEN** the listing is filtered to Somerville and Cambridge after the second pick, and to Cambridge alone after the removal, and Cambridge is shown as a chip

#### Scenario: Two towns in a metro
- **WHEN** a visitor opens `/?metro=ma-boston-metro-region&town=Somerville, MA&town=Cambridge, MA`
- **THEN** only events at venues in Somerville and Cambridge are listed, and the town multi-select shows both selected

#### Scenario: Towns offered
- **WHEN** a visitor has chosen the Boston Metro Region
- **THEN** the town options are the towns of the metro's venues, such as Boston, Cambridge and Somerville, and no town without a venue

#### Scenario: Town outside the metro
- **WHEN** a visitor opens `/?metro=ma-boston-metro-region&town=Burlington, VT`
- **THEN** the whole Boston Metro Region is listed, and no town is selected

#### Scenario: Town without a metro
- **WHEN** a visitor opens `/?town=Somerville, MA`
- **THEN** the listing isn't narrowed by town

#### Scenario: Remembered
- **WHEN** a visitor opens `/?metro=ma-boston-metro-region&town=Somerville, MA`, and later opens `/`
- **THEN** the second request redirects to the same metro and town

#### Scenario: Calendar feed
- **WHEN** a calendar app fetches `/calendar.ics?metro=ma-boston-metro-region&town=Somerville, MA`
- **THEN** the feed holds only Somerville events
