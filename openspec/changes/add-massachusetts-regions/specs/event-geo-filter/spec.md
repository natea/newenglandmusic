## RENAMED Requirements

- FROM: `### Requirement: A venue belongs to an area by the sheet's rules`
- TO: `### Requirement: A venue belongs to an area by its rules`

## MODIFIED Requirements

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
The site and the admin SHALL offer as options only areas whose rules list at least one state. Options SHALL appear in the order the site's area data lists them. Each area SHALL have a URL value made from its label; for metro areas, the value SHALL include the state, so that two states' "North" metros don't clash.

#### Scenario: Area with no states
- **WHEN** the area data lists the region "Northeast Corridor" with no states
- **THEN** "Northeast Corridor" isn't offered on the site or in the admin

#### Scenario: Sheet order
- **WHEN** the area data lists the regions Chesapeake Bay, Mid-Atlantic and New England, in that order
- **THEN** the Region options appear in that order

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
Once a metro area is chosen, the filter SHALL offer the towns in it that have at least one venue, by the venues' town and state, in alphabetical order, as a multi-select. The `town` URL parameter SHALL name a chosen town as "<town>, <state code>", such as `town=Somerville, MA`, and MAY be repeated. When towns are chosen, the listing, the calendar's event dates, the day maps and the calendar feeds SHALL include only events at venues in those towns. A town outside the chosen metro, or unknown, SHALL be ignored. Choosing no town SHALL mean the whole metro. Without a metro, `town` SHALL be ignored. The chosen towns SHALL be kept in the remembered filter, and in the month links, like the other filters. The multi-select SHALL work without JavaScript. Changing the metro SHALL drop towns that aren't in the new one.

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
Once one or more towns are chosen in the town filter, the filter SHALL offer the neighborhoods of those towns' venues, by neighborhood and town, in alphabetical order, as removable chips like the towns. A plain multi-select SHALL be offered without JavaScript. The `neighborhood` URL parameter SHALL name a chosen neighborhood as "<neighborhood>, <town>, <state code>", and MAY be repeated. When neighborhoods are chosen, the listing, the calendar's event dates, the day maps and the calendar feeds SHALL include only events at venues in those neighborhoods. A neighborhood outside the chosen towns, or unknown, SHALL be ignored. Without a chosen town, `neighborhood` SHALL be ignored. Chosen neighborhoods SHALL be remembered with the rest of the filter, and kept in the month links. Choosing no neighborhood SHALL mean the whole of the chosen towns.

#### Scenario: Two neighborhoods
- **WHEN** a visitor has chosen Boston, MA in Downtown & Central Boston, and picks "West End" and "Beacon Hill"
- **THEN** only events at venues in those neighborhoods are listed, and both show as chips

#### Scenario: No town chosen
- **WHEN** a visitor opens `/?metro=ma-downtown-central-boston&neighborhood=West End, Boston, MA`
- **THEN** the neighborhood is ignored, and the whole sub-region is listed

#### Scenario: Neighborhood from another town
- **WHEN** a visitor has chosen Cambridge, MA and the URL names "West End, Boston, MA"
- **THEN** it's ignored, and all of Cambridge is listed

## ADDED Requirements

### Requirement: Massachusetts is divided into sub-regions
Massachusetts's metros SHALL be the editors' 30 sub-regions, each with a label ("MA: The Berkshires"), its group, and its towns, in seven groups: Western Massachusetts, Central Massachusetts, MetroWest, Greater Boston, Northeast Massachusetts, South of Boston & Southeast, and Cape Cod & the Islands. Every Massachusetts venue SHALL belong to exactly one sub-region, chosen in this order: the sub-region listing its town; for a Boston venue, the sub-region listing its neighborhood (by name or alias); otherwise its county's default sub-region.

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
The seven Massachusetts metros the sheet defined (`ma-berkshires`, `ma-boston`, `ma-boston-metro-region`, `ma-cape-cod`, `ma-central`, `ma-north-shore`, `ma-south-shore-coast`) SHALL be read, wherever a metro is given (the listing, the remembered filter and the calendar feeds), as the state Massachusetts, so an old link or a subscribed feed keeps showing Massachusetts's shows rather than every area's.

#### Scenario: An old listing link
- **WHEN** a visitor opens `/?metro=ma-boston-metro-region`
- **THEN** the listing shows all Massachusetts events, with Massachusetts chosen

#### Scenario: A subscribed feed
- **WHEN** a calendar app fetches `/calendar.ics?metro=ma-cape-cod`
- **THEN** the feed holds Massachusetts's events, and no others
