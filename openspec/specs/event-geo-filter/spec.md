# event-geo-filter Specification

## Purpose
Lets visitors and admins narrow the events listing, and the admin event and venue lists, to one region, state or metro area. These are the areas the venue sheet defines, so the site browses the same geography as the Music Map.

## Requirements

### Requirement: A venue belongs to an area by its rules
Each region, state and metro area SHALL be defined in the site's own data, not the venue sheet, with its matching rules: a list of states, plus optional lists of counties and cities, and, for Massachusetts's sub-regions, neighborhoods and the counties it takes by default (below). A venue SHALL belong to an area other than a Massachusetts sub-region when its state is in the area's states and either:
- the area has no county or city lists, or
- the venue's county is in the county list, or its city is in the city list.

Comparisons SHALL ignore case and surrounding whitespace. A venue MAY belong to several areas at once, but to only one Massachusetts sub-region. Events SHALL belong to the areas of their linked venue, and an event with no linked venue SHALL belong to no area.

#### Scenario: State-only region
- **WHEN** the region "New England: South" lists the states CT, MA and RI
- **THEN** every venue in CT, MA or RI belongs to it, and no venue in NH does

#### Scenario: Metro matched by county
- **WHEN** the metro "NH: South" lists the state NH and the counties Cheshire, Hillsborough, Merrimack and Rockingham
- **THEN** a NH venue in Hillsborough county belongs to it, and a NH venue in Grafton county does not

#### Scenario: Metro matched by county or city
- **WHEN** a metro lists the state NY, the county Kings and the city Yonkers
- **THEN** a NY venue in Kings county belongs to it, and so does a NY venue in Westchester county whose city is Yonkers

#### Scenario: Same county name in another state
- **WHEN** a venue is in Middlesex county, CT, and the Massachusetts sub-region "MA: MetroWest" takes Middlesex county by default
- **THEN** the venue doesn't belong to "MA: MetroWest"

#### Scenario: Nested metros
- **WHEN** a venue is in Kings county, NY
- **THEN** it belongs to both "NY: NYC" and "NY: NYC Metro Region"

#### Scenario: Event without a venue
- **WHEN** an event has no linked venue
- **THEN** it doesn't match any region, state or metro filter

### Requirement: Only areas that can match appear as options
The site SHALL offer as Region, State and Metro Area options only areas whose rules list at least one state and whose states are all New England states, comparing state codes ignoring case, as the membership rules do (the area data stores states lowercase). The admin SHALL offer every area with at least one state, and its filters SHALL resolve every such area's value. Options SHALL appear in the order the site's area data lists them. Each area SHALL have a URL value made from its label; for metro areas, the value SHALL include the state, so that two states' "North" metros don't clash.

#### Scenario: Area with no states
- **WHEN** the area data lists the region "Northeast Corridor" with no states
- **THEN** "Northeast Corridor" isn't offered on the site or in the admin

#### Scenario: Sheet order
- **WHEN** the area data lists the regions Chesapeake Bay, Mid-Atlantic and New England, in that order
- **THEN** the Region options appear in that order

#### Scenario: Regions outside New England
- **WHEN** the area data lists the regions Chesapeake Bay, Mid-Atlantic and Tri-State, whose states include some outside New England
- **THEN** none is offered on the site, though all are still offered in the admin

#### Scenario: States outside New England
- **WHEN** the area data lists the states DC, Delaware, Maryland, New Jersey, New York and Pennsylvania
- **THEN** none is offered as a State option, and Massachusetts, Connecticut, Rhode Island, New Hampshire, Maine and Vermont are

#### Scenario: Metros of removed states
- **WHEN** the area data lists the metro "NY: Hudson Valley"
- **THEN** it isn't offered as a Metro Area option, and no group for New York appears

#### Scenario: Lowercase area states
- **WHEN** the areas store their states in lowercase, such as `ma`, `ct` and `ri`
- **THEN** New England and its metros are still offered on the site

#### Scenario: Admin sidebar keeps every area
- **WHEN** an admin opens the event list and the area data lists the Tri-State region and the NY: Hudson Valley metro
- **THEN** the admin's Region and Metro Area filters offer both, and filtering by either still resolves

### Requirement: Visitors can filter the events listing by region, state and metro area
The homepage and the month archive pages SHALL offer State and Metro Area filters, and no Region menu: New England's regions are few, and picking a state is simpler. Region, state and metro SHALL be chosen with the `region`, `state` and `metro` URL query parameters, and SHALL work without JavaScript; a `region` parameter (from an old link, a remembered filter or a calendar feed) SHALL still apply. When a filter is set, the event list, the calendar's event dates and the day maps SHALL include only events that belong to the chosen areas. Filters given together SHALL all apply. With no filter set, the page SHALL show every event the site lists, which are the New England events.

#### Scenario: Filter by state
- **WHEN** a visitor opens `/?state=vermont`
- **THEN** only events at Vermont venues are listed, and the State filter shows Vermont as selected

#### Scenario: Filter by metro area
- **WHEN** a visitor opens `/?metro=ma-north-of-the-charles`
- **THEN** only events at venues in that sub-region are listed

#### Scenario: Region and state together
- **WHEN** a visitor opens `/?region=new-england-north&state=massachusetts`
- **THEN** no events are listed, and the page says that no events match the filters and links to the unfiltered listing

#### Scenario: Month archive
- **WHEN** a visitor opens `/2026-11/?region=new-england-north`
- **THEN** only November events at venues in ME, NH or VT are listed

#### Scenario: No filter
- **WHEN** a visitor with no remembered filter opens `/` with no filter parameters
- **THEN** events from every New England venue are listed

#### Scenario: No region menu
- **WHEN** a visitor opens `/`
- **THEN** the filter offers State and Metro Area menus, and no Region menu

### Requirement: The metro area options follow the chosen state
When a state is chosen, the Metro Area options SHALL list only that state's metros. With no state chosen, the options SHALL list every metro, grouped by state, except that Massachusetts's sub-regions SHALL be grouped under their own groups' names (such as "Western Massachusetts") in the areas' order. A metro that belongs to a different state from the chosen state SHALL be ignored. A state with no metros SHALL show no Metro Area options.

#### Scenario: Metros narrowed to the state
- **WHEN** a visitor has chosen Massachusetts
- **THEN** the Metro Area options are Massachusetts's sub-regions, such as The Berkshires, North of the Charles and Outer Cape, under their groups' names, and no metros from other states

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
- **THEN** the page returns 200 and lists the unfiltered New England events

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
- **WHEN** an admin filters the all-events list to the metro "MA: North of the Charles" and to unapproved events
- **THEN** only unapproved events at venues in that sub-region are listed

#### Scenario: Venues by region
- **WHEN** an admin filters the venue list to the region "Tri-State"
- **THEN** only venues in CT, NJ or NY are listed

#### Scenario: Admin metro list follows the state
- **WHEN** an admin has chosen the State filter "Vermont"
- **THEN** the Metro Area filter lists only "VT: North" and "VT: South"

### Requirement: Visitors can narrow a metro area to some of its towns
Once a metro area is chosen, the filter SHALL offer the towns in it that have at least one venue, if there are two or more, by the venues' town and state, in alphabetical order, as a multi-select. The `town` URL parameter SHALL name a chosen town as "<town>, <state code>", such as `town=Somerville, MA`, and MAY be repeated. When towns are chosen, the listing, the calendar's event dates, the day maps and the calendar feeds SHALL include only events at venues in those towns. A town outside the chosen metro, or unknown, SHALL be ignored. Choosing no town SHALL mean the whole metro. Without a metro, `town` SHALL be ignored. The chosen towns SHALL be kept in the remembered filter, and in the month links, like the other filters. The multi-select SHALL work without JavaScript. Changing the metro SHALL drop towns that aren't in the new one. A metro with only one town SHALL offer no town filter.

With JavaScript, the multi-select SHALL be shown as an "add a town" list beside the chosen towns. Each chosen town SHALL be shown as a chip with a button to remove it. Choosing a town from the list SHALL add it, and removing one SHALL drop it. Either SHALL apply the filter at once. Towns already chosen SHALL NOT be offered again in the list.

#### Scenario: Adding and removing towns
- **WHEN** a visitor with North of the Charles chosen picks Somerville, then Cambridge, from "add a town", then removes Somerville with its ×
- **THEN** the listing is filtered to Somerville and Cambridge after the second pick, and to Cambridge alone after the removal, and Cambridge is shown as a chip

#### Scenario: Two towns in a metro
- **WHEN** a visitor opens `/?metro=ma-north-of-the-charles&town=Somerville, MA&town=Cambridge, MA`
- **THEN** only events at venues in Somerville and Cambridge are listed, and the town multi-select shows both selected

#### Scenario: Towns offered
- **WHEN** a visitor has chosen North of the Charles
- **THEN** the town options are the towns of the sub-region's venues, such as Cambridge, Medford and Somerville, and no town without a venue

#### Scenario: A metro with one town
- **WHEN** a visitor chooses Downtown & Central Boston, whose venues are all in Boston
- **THEN** no town filter is offered, and Boston's neighborhoods are

#### Scenario: Town outside the metro
- **WHEN** a visitor opens `/?metro=ma-north-of-the-charles&town=Burlington, VT`
- **THEN** the whole of North of the Charles is listed, and no town is selected

#### Scenario: Town without a metro
- **WHEN** a visitor opens `/?town=Somerville, MA`
- **THEN** the listing isn't narrowed by town

#### Scenario: Remembered
- **WHEN** a visitor opens `/?metro=ma-north-of-the-charles&town=Somerville, MA`, and later opens `/`
- **THEN** the second request redirects to the same metro and town

#### Scenario: Calendar feed
- **WHEN** a calendar app fetches `/calendar.ics?metro=ma-north-of-the-charles&town=Somerville, MA`
- **THEN** the feed holds only Somerville events

### Requirement: Visitors can narrow chosen towns to some of their neighborhoods
Once one or more towns are chosen in the town filter, or a metro with only one town is chosen, the filter SHALL offer the neighborhoods of those towns' venues (or that one town's), by neighborhood and town, in alphabetical order, as removable chips like the towns. A plain multi-select SHALL be offered without JavaScript. The `neighborhood` URL parameter SHALL name a chosen neighborhood as "<neighborhood>, <town>, <state code>", and MAY be repeated. When neighborhoods are chosen, the listing, the calendar's event dates, the day maps and the calendar feeds SHALL include only events at venues in those neighborhoods. A neighborhood outside the chosen towns, or unknown, SHALL be ignored. Without a chosen town, `neighborhood` SHALL be ignored, unless the metro has only one town. Chosen neighborhoods SHALL be remembered with the rest of the filter, and kept in the month links. Choosing no neighborhood SHALL mean the whole of the chosen towns.

#### Scenario: Two neighborhoods
- **WHEN** a visitor has chosen Downtown & Central Boston, and picks "West End" and "Beacon Hill"
- **THEN** only events at venues in those neighborhoods are listed, and both show as chips

#### Scenario: No town chosen
- **WHEN** a visitor opens `/?metro=ma-north-of-the-charles&neighborhood=Davis Square, Somerville, MA`
- **THEN** the neighborhood is ignored, and the whole sub-region is listed

#### Scenario: Neighborhood from another town
- **WHEN** a visitor has chosen Cambridge, MA and the URL names "West End, Boston, MA"
- **THEN** it's ignored, and all of Cambridge is listed

### Requirement: Massachusetts is divided into sub-regions
Massachusetts's metros SHALL be the editors' 28 sub-regions, each with a label ("MA: The Berkshires"), its group, and its towns, in seven groups: Western Massachusetts, Central Massachusetts, MetroWest, Greater Boston, Northeast Massachusetts, South of Boston & Southeast, and Cape Cod & the Islands. Every Massachusetts venue SHALL belong to exactly one sub-region, chosen in this order: the sub-region listing its town; for a Boston venue, the sub-region listing its neighborhood (by name or alias); otherwise its county's default sub-region.

#### Scenario: A listed town
- **WHEN** a Massachusetts venue's town is Northampton
- **THEN** it belongs to "MA: Pioneer Valley / Connecticut River Valley" and to no other sub-region

#### Scenario: A Boston neighborhood
- **WHEN** a Boston venue's neighborhood is "Fenway-Kenmore", or its town is given as "Jamaica Plain"
- **THEN** the first belongs to "MA: Downtown & Central Boston" and the second to "MA: Boston Neighborhoods"

#### Scenario: A town the list doesn't name
- **WHEN** a Massachusetts venue is in Woburn, Middlesex county, which no sub-region lists
- **THEN** it belongs to Middlesex county's default sub-region, and to no other

#### Scenario: Every venue placed
- **WHEN** the sub-regions are loaded
- **THEN** every active Massachusetts venue with a county belongs to exactly one sub-region

### Requirement: Old Massachusetts metro addresses still cover Massachusetts
The Massachusetts metros the sheet defined whose addresses no sub-region takes over (`ma-berkshires`, `ma-boston`, `ma-boston-metro-region`, `ma-cape-cod`, `ma-central`, `ma-south-shore-coast`) SHALL be read, wherever a metro is given (the listing, the remembered filter and the calendar feeds), as the state Massachusetts, so an old link or a subscribed feed keeps showing Massachusetts's shows rather than every area's.

#### Scenario: An old listing link
- **WHEN** a visitor opens `/?metro=ma-boston-metro-region`
- **THEN** the listing shows all Massachusetts events, with Massachusetts chosen

#### Scenario: A subscribed feed
- **WHEN** a calendar app fetches `/calendar.ics?metro=ma-cape-cod`
- **THEN** the feed holds Massachusetts's events, and no others

#### Scenario: The North Shore address kept
- **WHEN** a visitor opens `/?metro=ma-north-shore`
- **THEN** the listing shows the new North Shore sub-region's events, with it chosen
