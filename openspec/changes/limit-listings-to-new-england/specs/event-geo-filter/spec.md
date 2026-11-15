## MODIFIED Requirements

### Requirement: Only areas that can match appear as options
The site SHALL offer as Region, State and Metro Area options only areas whose rules list at least one state and whose states are all New England states, comparing state codes ignoring case, as the membership rules do (the sheet's area states are stored lowercase). The admin SHALL offer every area with at least one state, and its filters SHALL resolve every such area's value. Options SHALL appear in the sheet's row order. Each area SHALL have a URL value made from its label; for metro areas, the value SHALL include the state, so that two states' "North" metros don't clash.

#### Scenario: Area with no states
- **WHEN** the sheet lists the region "Northeast Corridor" with no states
- **THEN** "Northeast Corridor" isn't offered on the site or in the admin

#### Scenario: Sheet order
- **WHEN** the sheet lists the regions New England, New England: South and New England: North, in that order
- **THEN** the Region options appear in that order

#### Scenario: Regions outside New England
- **WHEN** the sheet lists the regions Chesapeake Bay, Mid-Atlantic and Tri-State, whose states include some outside New England
- **THEN** none is offered on the site, though all are still offered in the admin

#### Scenario: States outside New England
- **WHEN** the sheet lists the states DC, Delaware, Maryland, New Jersey, New York and Pennsylvania
- **THEN** none is offered as a State option, and Massachusetts, Connecticut, Rhode Island, New Hampshire, Maine and Vermont are

#### Scenario: Metros of removed states
- **WHEN** the sheet lists the metro "NY: Hudson Valley"
- **THEN** it isn't offered as a Metro Area option, and no group for New York appears

#### Scenario: Lowercase sheet states
- **WHEN** the sheet's areas store their states in lowercase, such as `ma`, `ct` and `ri`
- **THEN** New England and its metros are still offered on the site

#### Scenario: Admin sidebar keeps every area
- **WHEN** an admin opens the event list and the sheet lists the Tri-State region and the NY: Hudson Valley metro
- **THEN** the admin's Region and Metro Area filters offer both, and filtering by either still resolves

### Requirement: Visitors can filter the events listing by region, state and metro area
The homepage and the month archive pages SHALL offer Region, State and Metro Area filters. They SHALL be chosen with the `region`, `state` and `metro` URL query parameters and SHALL work without JavaScript. When a filter is set, the event list, the calendar's event dates and the day maps SHALL include only events that belong to the chosen areas. Filters given together SHALL all apply. With no filter set, the page SHALL show every event the site lists, which are the New England events.

#### Scenario: Filter by state
- **WHEN** a visitor opens `/?state=vermont`
- **THEN** only events at Vermont venues are listed, and the State filter shows Vermont as selected

#### Scenario: Filter by metro area
- **WHEN** a visitor opens `/?metro=ma-boston-metro-region`
- **THEN** only events at venues in that metro's towns are listed

#### Scenario: Region and state together
- **WHEN** a visitor opens `/?region=new-england-north&state=massachusetts`
- **THEN** no events are listed, and the page says that no events match the filters and links to the unfiltered listing

#### Scenario: Month archive
- **WHEN** a visitor opens `/2026-11/?region=new-england-north`
- **THEN** only November events at venues in ME, NH or VT are listed

#### Scenario: No filter
- **WHEN** a visitor with no remembered filter opens `/` with no filter parameters
- **THEN** events from every New England venue are listed

### Requirement: The metro area options follow the chosen state
When a state is chosen, the Metro Area options SHALL list only that state's metros. With no state chosen, the options SHALL list every metro, grouped by state. A metro that belongs to a different state from the chosen state SHALL be ignored. A state with no metros SHALL show no Metro Area options.

#### Scenario: Metros narrowed to the state
- **WHEN** a visitor has chosen Massachusetts
- **THEN** the Metro Area options are the Massachusetts metros, such as Berkshires, Boston Metro Region and Cape Cod, and no metros from other states

#### Scenario: Metro from another state
- **WHEN** a visitor opens `/?state=massachusetts&metro=vt-north`
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
