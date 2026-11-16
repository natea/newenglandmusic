## MODIFIED Requirements

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

### Requirement: Filters survive navigation and bad input
The previous, current and next month links SHALL keep the chosen filters. An unknown or stale filter value SHALL be ignored, as though it wasn't given, and SHALL NOT cause an error page.

#### Scenario: Month links keep the filter
- **WHEN** a visitor on `/?state=maine` follows the next-month link
- **THEN** the next month's archive opens with `state=maine` still applied

#### Scenario: Unknown value
- **WHEN** a visitor opens `/?state=atlantis`
- **THEN** the page returns 200 and lists the unfiltered New England events
