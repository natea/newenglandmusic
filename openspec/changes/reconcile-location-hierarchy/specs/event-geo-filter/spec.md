# Spec Delta

## ADDED Requirements

### Requirement: A venue belongs to an area by its placement
The areas SHALL be the states, regions and sub-regions of the site's list of places (`place-hierarchy`). A venue SHALL belong to a state when its state is that state, to a sub-region when its stored placement (`venue-placement`) is that sub-region, and to a region when its sub-region is in that region. Events SHALL belong to the areas of their linked venue, and an event with no linked venue SHALL belong to no area.

#### Scenario: Sub-region
- **WHEN** a venue is placed in the sub-region North of the Charles
- **THEN** it belongs to North of the Charles, to its region Greater Boston and to Massachusetts, and to no other sub-region or region

#### Scenario: No county rule
- **WHEN** a Massachusetts venue is in Woburn, which the list puts in Merrimack Valley / Greater Lowell, and its county text is Middlesex
- **THEN** it belongs to Merrimack Valley / Greater Lowell, and not to MetroWest

#### Scenario: Unplaced venue
- **WHEN** a Rhode Island venue has no matched town
- **THEN** it belongs to Rhode Island and to no region or sub-region

#### Scenario: Event without a venue
- **WHEN** an event has no linked venue
- **THEN** it doesn't match any state, region or sub-region filter

### Requirement: Visitors can filter the events listing by state, region and sub-region
The homepage and the month archive pages SHALL offer State, Region and Sub-region filters, chosen with the `state`, `region` and `subregion` URL query parameters, and SHALL work without JavaScript. When a filter is set, the event list, the calendar's event dates and the day maps SHALL include only events that belong to the chosen areas. With no filter set, the page SHALL show every New England event.

#### Scenario: Filter by state
- **WHEN** a visitor opens `/?state=vermont`
- **THEN** only events at Vermont venues are listed, and the State filter shows Vermont as selected

#### Scenario: Filter by region
- **WHEN** a visitor opens `/?region=ma-greater-boston`
- **THEN** only events at venues in Greater Boston's sub-regions are listed, and Massachusetts and Greater Boston show as selected

#### Scenario: Filter by sub-region
- **WHEN** a visitor opens `/?subregion=ma-north-of-the-charles`
- **THEN** only events at venues in that sub-region are listed, and Massachusetts, Greater Boston and North of the Charles show as selected

#### Scenario: No filter
- **WHEN** a visitor with no remembered filter opens `/` with no filter parameters
- **THEN** events from every New England venue are listed

#### Scenario: No matching events
- **WHEN** a visitor opens the address of a sub-region whose venues have no upcoming events
- **THEN** the page says that no events match the filters and links to the unfiltered listing

### Requirement: The region and sub-region are remembered like the state
The `region` and `subregion` parameters SHALL be saved in the remembered filter, kept in the previous, current and next month links, and cleared, exactly as `state` is. A page opened with either parameter SHALL count as opened with a filter, so the remembered filter doesn't redirect it.

#### Scenario: Sub-region is remembered
- **WHEN** a visitor opens `/?subregion=nh-portsmouth-area` and later opens `/`
- **THEN** the second request redirects to the same sub-region

#### Scenario: Month links keep the sub-region
- **WHEN** a visitor on `/?subregion=nh-portsmouth-area` follows the next-month link
- **THEN** the next month's archive opens with the same sub-region applied

#### Scenario: A link wins over the remembered filter
- **WHEN** a visitor whose cookie holds `state=vermont` opens `/?region=ma-greater-boston`
- **THEN** Greater Boston's events are listed, with no redirect

### Requirement: Each menu follows the choice above it
The Region menu SHALL list the chosen state's regions, or every state's regions grouped by state when no state is chosen. The Sub-region menu SHALL be offered only once a region is chosen, and SHALL list that region's sub-regions. A region with fewer than two offered sub-regions SHALL have no Sub-region menu. A region outside the chosen state, or a sub-region outside the chosen region or state, SHALL be ignored.

#### Scenario: Regions narrowed to the state
- **WHEN** a visitor has chosen New Hampshire
- **THEN** the Region options are New Hampshire's regions, such as Seacoast and Merrimack Valley, and no other state's

#### Scenario: No state chosen
- **WHEN** a visitor has chosen nothing
- **THEN** the Region options list every state's regions under their state's name, and no Sub-region menu is shown

#### Scenario: Sub-regions of the region
- **WHEN** a visitor has chosen the region Greater Boston
- **THEN** the Sub-region options are Greater Boston's, such as North of the Charles and Inner West Suburbs

#### Scenario: A region with one sub-region
- **WHEN** a visitor chooses Greater Portland & Casco Bay, whose only sub-region is Greater Portland
- **THEN** no Sub-region menu is shown, and the town filter is offered for the region

#### Scenario: Region from another state
- **WHEN** a visitor opens `/?state=maine&region=ma-greater-boston`
- **THEN** the listing shows all Maine events, and no region is selected

#### Scenario: Sub-region from another region
- **WHEN** a visitor opens `/?region=ma-greater-boston&subregion=ma-berkshires`
- **THEN** the listing shows all of Greater Boston, and no sub-region is selected

### Requirement: Visitors can narrow an area to some of its towns
Once a region or sub-region is chosen, the filter SHALL offer the list's towns in the narrowest chosen area that have at least one active venue, if there are two or more, in alphabetical order. The `town` parameter SHALL name a town as "<town>, <state code>" and MAY be repeated. Chosen towns SHALL narrow the listing, the calendar's event dates, the day maps and the calendar feeds to venues matched to them, and SHALL be remembered and kept in the month links.

#### Scenario: Two towns in a sub-region
- **WHEN** a visitor opens `/?subregion=ma-north-of-the-charles&town=Somerville, MA&town=Cambridge, MA`
- **THEN** only events at venues matched to Somerville and Cambridge are listed, and both show as chips

#### Scenario: Towns are the list's towns
- **WHEN** a visitor has chosen Pioneer Valley, where one venue gives its town as "Florence" and another as "Northampton"
- **THEN** the town options include Northampton and not Florence, and choosing Northampton lists both venues' events

#### Scenario: Towns of a region
- **WHEN** a visitor has chosen the region Seacoast and no sub-region
- **THEN** the town options are the towns with venues in all of Seacoast's sub-regions

#### Scenario: Only one town
- **WHEN** a visitor chooses Downtown & Central Boston, whose venues are all matched to Boston
- **THEN** no town filter is offered, and Boston's neighborhoods are

#### Scenario: Town outside the area
- **WHEN** a visitor opens `/?subregion=ma-north-of-the-charles&town=Burlington, VT`
- **THEN** the whole of North of the Charles is listed, and no town is selected

#### Scenario: Town without a region or sub-region
- **WHEN** a visitor opens `/?state=massachusetts&town=Somerville, MA`
- **THEN** the listing isn't narrowed by town

### Requirement: Towns are chosen as chips
The town filter SHALL be a multi-select that works without JavaScript. With JavaScript, it SHALL be shown as an "add a town" list beside the chosen towns, each a chip with a button to remove it. Adding or removing a town SHALL apply the filter at once, and a town already chosen SHALL NOT be offered again.

#### Scenario: Adding and removing towns
- **WHEN** a visitor with North of the Charles chosen picks Somerville, then Cambridge, from "add a town", then removes Somerville with its ×
- **THEN** the listing is filtered to Somerville and Cambridge after the second pick, and to Cambridge alone after the removal

#### Scenario: Without JavaScript
- **WHEN** a visitor without JavaScript selects two towns in the multi-select and submits the form
- **THEN** the listing is filtered to those two towns

### Requirement: Old addresses still work
Wherever a filter is read (the listing, the remembered filter, the calendar feeds and saved weekly email choices), an old `metro` value SHALL be read as the sub-region that took over its address, or else as that metro's state. The old `region` values `new-england`, `new-england-north` and `new-england-south` SHALL still select their states. An old `town` value that is another name for a town SHALL select that town, and its listed neighborhood when it names one.

#### Scenario: A Massachusetts sub-region's old address
- **WHEN** a visitor opens `/?metro=ma-north-of-the-charles`
- **THEN** the listing shows North of the Charles, with it chosen as the sub-region

#### Scenario: A renamed sub-region
- **WHEN** a visitor opens `/?metro=ma-pioneer-valley-connecticut-river-valley`
- **THEN** the listing shows the sub-region Pioneer Valley

#### Scenario: Another state's old metro
- **WHEN** a visitor opens `/?metro=nh-south`
- **THEN** the listing shows all New Hampshire events, with New Hampshire chosen

#### Scenario: An older Massachusetts metro
- **WHEN** a visitor opens `/?metro=ma-boston-metro-region`
- **THEN** the listing shows all Massachusetts events, with Massachusetts chosen

#### Scenario: An old multi-state region
- **WHEN** a visitor opens `/2026-11/?region=new-england-north`
- **THEN** only November events at venues in ME, NH or VT are listed

#### Scenario: An old town value
- **WHEN** a visitor opens `/?metro=ma-boston-neighborhoods&town=Allston, MA`
- **THEN** the listing shows events at venues in Boston's listed neighborhood Allston-Brighton

#### Scenario: A remembered metro
- **WHEN** a visitor whose cookie holds `metro=ma-north-shore` opens `/`
- **THEN** the request redirects to `/?subregion=ma-north-shore`

### Requirement: Admins can filter events and venues by state, region and sub-region
The admin's event list, its all-events list (`/admin/core/alleventproxy/`) and its venue list SHALL have State, Region and Sub-region sidebar filters that use the same areas and placement as the site, and combine with the other admin filters. The Region filter SHALL list the chosen state's regions, and the Sub-region filter the chosen region's or state's sub-regions. With no state or region chosen, the Sub-region filter SHALL list none.

#### Scenario: Review queue for one sub-region
- **WHEN** an admin filters the all-events list to the sub-region North of the Charles and to unapproved events
- **THEN** only unapproved events at venues in that sub-region are listed

#### Scenario: Venues by region
- **WHEN** an admin filters the venue list to the region Seacoast
- **THEN** only venues placed in Seacoast's sub-regions are listed

#### Scenario: Sub-regions follow the region
- **WHEN** an admin has chosen the Region filter "Monadnock"
- **THEN** the Sub-region filter lists only Keene Area and Milford Area

#### Scenario: A state outside New England
- **WHEN** an admin chooses the State filter "New York"
- **THEN** New York's venues are listed, and the Region filter lists no regions

### Requirement: Only areas with venues appear as options
The site SHALL offer as State options the six New England states, and as Region and Sub-region options only those with at least one active venue placed in them, in the order the regions file lists them. An area that isn't offered SHALL still be resolved when a URL names it. The admin SHALL offer every state the site holds, and every region and sub-region whether or not it has a venue.

#### Scenario: A sub-region with no venue
- **WHEN** no active venue is placed in the sub-region Elizabeth Islands
- **THEN** it isn't offered as a Sub-region option on the site, and it is in the admin

#### Scenario: A region with no venue
- **WHEN** no active venue is placed in any sub-region of the region Great North Woods
- **THEN** it isn't offered as a Region option on the site

#### Scenario: An address for an area that isn't offered
- **WHEN** a visitor opens `/?subregion=ma-elizabeth-islands`
- **THEN** the page returns 200, says that no events match the filters, and links to the unfiltered listing

#### Scenario: File order
- **WHEN** the file lists Massachusetts's regions from Western Massachusetts to Cape Cod & the Islands
- **THEN** the Region options for Massachusetts appear in that order

#### Scenario: States outside New England
- **WHEN** the site holds venues in New York and Pennsylvania
- **THEN** neither state is offered as a State option on the site, and both are in the admin

#### Scenario: Areas outside New England
- **WHEN** an admin opens the event list
- **THEN** its Region filter doesn't list Tri-State, and no filter lists "NY: Hudson Valley"

## MODIFIED Requirements

### Requirement: Visitors can narrow chosen towns to some of their neighborhoods
Once one or more towns are chosen in the town filter, or an area whose venues are all in one town is chosen, the filter SHALL offer those towns' neighborhoods, by neighborhood and town, in alphabetical order, as removable chips like the towns. A plain multi-select SHALL be offered without JavaScript. For a town with listed neighborhoods, the options SHALL be the listed neighborhoods that have at least one active venue and, when a sub-region is chosen, are in it; for any other town, they SHALL be its venues' own neighborhoods. The `neighborhood` URL parameter SHALL name a chosen neighborhood as "<neighborhood>, <town>, <state code>", MAY be repeated, and MAY use another name of a listed neighborhood. When neighborhoods are chosen, the listing, the calendar's event dates, the day maps and the calendar feeds SHALL include only events at venues in those neighborhoods. A neighborhood outside the chosen towns, or unknown, SHALL be ignored. Without a chosen town, `neighborhood` SHALL be ignored, unless the area's venues are all in one town. Chosen neighborhoods SHALL be remembered with the rest of the filter, and kept in the month links. Choosing no neighborhood SHALL mean the whole of the chosen towns.

#### Scenario: Two neighborhoods
- **WHEN** a visitor has chosen Downtown & Central Boston, and picks "West End" and "Beacon Hill"
- **THEN** only events at venues in those neighborhoods are listed, and both show as chips

#### Scenario: No town chosen
- **WHEN** a visitor opens `/?subregion=ma-north-of-the-charles&neighborhood=Davis Square, Somerville, MA`
- **THEN** the neighborhood is ignored, and the whole sub-region is listed

#### Scenario: Neighborhood from another town
- **WHEN** a visitor has chosen Cambridge, MA and the URL names "West End, Boston, MA"
- **THEN** it's ignored, and all of Cambridge is listed

#### Scenario: Listed neighborhoods
- **WHEN** a visitor has chosen Downtown & Central Boston, where a venue's own neighborhood is "Fenway-Kenmore"
- **THEN** the options include "Fenway, Boston, MA" and not "Fenway-Kenmore, Boston, MA", and choosing Fenway lists that venue's events

#### Scenario: Only the sub-region's neighborhoods
- **WHEN** a visitor has chosen the sub-region Boston Neighborhoods
- **THEN** the options include Jamaica Plain and not Back Bay

#### Scenario: A town without listed neighborhoods
- **WHEN** a visitor has chosen Portland, ME, whose venues' own neighborhoods include "Old Port"
- **THEN** the options include "Old Port, Portland, ME"

#### Scenario: An old neighborhood value
- **WHEN** the URL names "Fenway-Kenmore, Boston, MA" with Downtown & Central Boston chosen
- **THEN** it selects the listed neighborhood Fenway

## REMOVED Requirements

### Requirement: A venue belongs to an area by its rules
**Reason**: Areas no longer have lists of states, counties and cities. A venue's area comes from its stored placement in the list of places.
**Migration**: See "A venue belongs to an area by its placement" above, and `venue-placement`.

### Requirement: Visitors can filter the events listing by region, state and metro area
**Reason**: "Metro area" is replaced by the list's regions and sub-regions, and the site now offers a Region menu.
**Migration**: See "Visitors can filter the events listing by state, region and sub-region". Old `metro` and `region` values keep working ("Old addresses still work").

### Requirement: The metro area options follow the chosen state
**Reason**: There is no metro menu. Regions follow the state, and sub-regions follow the region.
**Migration**: See "Each menu follows the choice above it".

### Requirement: Admins can filter events and venues by region, state and metro area
**Reason**: The admin's filters use the same hierarchy as the site, and the areas outside New England are removed.
**Migration**: See "Admins can filter events and venues by state, region and sub-region". Venues outside New England are still reached with the State filter.

### Requirement: Visitors can narrow a metro area to some of its towns
**Reason**: Towns are now the list's towns, offered under a region or a sub-region.
**Migration**: See "Visitors can narrow an area to some of its towns". Old `town` values keep working ("Old addresses still work").

### Requirement: Only areas that can match appear as options
**Reason**: Areas no longer carry lists of states, so "an area with no states" has no meaning, and the areas outside New England are removed. What is offered now depends on whether an area has a venue.
**Migration**: See "Only areas with venues appear as options".

### Requirement: Massachusetts is divided into sub-regions
**Reason**: Every state is now divided into regions and sub-regions by the editors' file, and a town the file lists is no longer placed by its county.
**Migration**: See `place-hierarchy` ("The site keeps one list of places") and `venue-placement` ("A placed venue is in exactly one sub-region and region").

### Requirement: Old Massachusetts metro addresses still cover Massachusetts
**Reason**: Every state's old metro addresses are now carried over, not only Massachusetts's.
**Migration**: See "Old addresses still work". `ma-berkshires`, once an older metro read as Massachusetts, is now the address of the sub-region Berkshires.
