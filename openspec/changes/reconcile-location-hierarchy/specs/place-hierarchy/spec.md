# Spec Delta

## Purpose

Keeps the site's one list of where places are: each New England state's regions, their sub-regions, the towns in each, and the neighborhoods the editors list for a town. The location picker, venue placement, feeds and exports all read this list, so they agree.

## ADDED Requirements

### Requirement: The site keeps one list of places
The site SHALL hold one hierarchy for the six New England states, taken from the editors' regions file kept in the repository: each state has regions, each region has sub-regions, and each sub-region has towns. Every town SHALL be in exactly one sub-region, every sub-region in exactly one region, and every region in exactly one state. Nothing else SHALL define regions, sub-regions or towns.

#### Scenario: A town's place
- **WHEN** the file lists Somerville under Massachusetts, Greater Boston, North of the Charles
- **THEN** Somerville is a town of the sub-region North of the Charles, in the region Greater Boston, in Massachusetts, and of no other sub-region

#### Scenario: Every town is loaded
- **WHEN** the file lists 1,602 towns and cities
- **THEN** the site holds 1,602 towns, including those with no venue

#### Scenario: Same name in two states
- **WHEN** the file lists a Burlington in Vermont, in Massachusetts, in Connecticut and in Maine
- **THEN** the site holds four towns named Burlington, one in each state

### Requirement: A town carries its Census details
Each town SHALL keep the Census Bureau's identifier, name, kind (such as town, city or plantation), county or county equivalent, and centre point that the file gives it. The site SHALL know a town by its Census identifier, so a town that is renamed or moved in a later file is still the same town.

#### Scenario: Connecticut's planning regions
- **WHEN** the file gives Hartford's county as "Capitol Planning Region"
- **THEN** the town Hartford records that county, whatever county text its venues carry

#### Scenario: A town moved in a later file
- **WHEN** a later file lists Woburn, with the same Census identifier, under a different sub-region
- **THEN** the same town is now in that sub-region, and isn't added a second time

### Requirement: Editors can list a town's neighborhoods
The file MAY list neighborhoods for a town. Each listed neighborhood SHALL belong to one town, and SHALL name the sub-region it is in, which MAY differ from the sub-region of the town's own row. A town with listed neighborhoods SHALL keep its own row's sub-region for venues that match none of them.

#### Scenario: Boston is split among sub-regions
- **WHEN** the file lists Boston's neighborhood Jamaica Plain under Boston Neighborhoods and Back Bay under Downtown & Central Boston
- **THEN** each neighborhood is in the sub-region its row names, and both belong to the town Boston

#### Scenario: A town without listed neighborhoods
- **WHEN** the file lists no neighborhood for Portland, Maine
- **THEN** Portland has no listed neighborhoods

### Requirement: Places have other names
The site SHALL keep, in its own data beside the file, other names for a town (a village or postal name, such as "Florence" for Northampton, MA) and for a listed neighborhood (such as "Fenway-Kenmore" for Fenway). A town's other name MAY also name one of that town's listed neighborhoods, such as "Allston" for Boston's Allston-Brighton. Another name SHALL point to exactly one town in its state.

#### Scenario: A village
- **WHEN** the other names list "Bellows Falls" for Rockingham, VT
- **THEN** "Bellows Falls, VT" names the town Rockingham

#### Scenario: A neighborhood used as a town
- **WHEN** the other names list "Allston" for Boston, MA and its neighborhood Allston-Brighton
- **THEN** "Allston, MA" names the town Boston and the listed neighborhood Allston-Brighton

#### Scenario: A name for two towns
- **WHEN** the other names list "Riverside" for two Massachusetts towns
- **THEN** the load fails and names the clash

### Requirement: Areas have display names and stable addresses
Each region and sub-region SHALL have a display name, which is the file's name unless the site's data gives another (the file writes Massachusetts's regions in capitals), and a URL value that starts with its state's code. A sub-region's URL value SHALL be its state code and its name, or, when two sub-regions of a state share a name, its state code, its region's name and its name.

#### Scenario: Capitals
- **WHEN** the file names a region "CAPE COD & THE ISLANDS"
- **THEN** it is shown as "Cape Cod & the Islands", with the URL value `ma-cape-cod-the-islands`

#### Scenario: Same region name in two states
- **WHEN** the file lists a region "Lower Connecticut River Valley" in Connecticut and in Vermont
- **THEN** their URL values are `ct-lower-connecticut-river-valley` and `vt-lower-connecticut-river-valley`

#### Scenario: A sub-region name used twice in a state
- **WHEN** Vermont lists a sub-region "Windham" under Okemo Valley and under Deerfield Valley
- **THEN** their URL values are `vt-okemo-valley-windham` and `vt-deerfield-valley-windham`

#### Scenario: A Massachusetts sub-region keeps its address
- **WHEN** the file lists the sub-region "North of the Charles" in Massachusetts
- **THEN** its URL value is `ma-north-of-the-charles`, as it was

### Requirement: A file with a fault is refused whole
Loading SHALL check the whole file before changing anything. It SHALL refuse the file, name each fault with its row, and leave the site's places as they were, when a row has no state, region, sub-region or town, names a state outside New England, repeats a town's Census identifier, repeats a town's name within a state, or lists a neighborhood for a town the file doesn't hold.

#### Scenario: A town listed twice
- **WHEN** the file lists Plymouth, Massachusetts under two sub-regions
- **THEN** the load fails, names both rows, and no place changes

#### Scenario: A neighborhood without its town
- **WHEN** the file lists a neighborhood of "Bostn"
- **THEN** the load fails and names the row

#### Scenario: A clean file
- **WHEN** the file has no fault
- **THEN** the load makes the site's regions, sub-regions, towns and listed neighborhoods match it

### Requirement: The site's places always match the file
Every deploy SHALL make the site's places match the file in the repository: places the file adds SHALL be added, changed ones updated, and ones it no longer lists removed. Loading the same file twice SHALL change nothing.

#### Scenario: A sub-region removed
- **WHEN** a later file no longer lists a sub-region, and its towns are listed under another
- **THEN** the sub-region is gone, and its towns are in the other

#### Scenario: Loaded twice
- **WHEN** the same file is loaded a second time
- **THEN** no place is added, changed or removed

### Requirement: A new file can be compared before it is adopted
A command SHALL take the path of a regions file and report, without changing anything: the faults that would refuse it; the regions, sub-regions, towns and neighborhoods it adds, removes, renames or moves; and the venues that would move to another sub-region or lose their place, by name and town.

#### Scenario: Comparing a new version
- **WHEN** an editor's next file moves Woburn to another sub-region, and the command is run with its path
- **THEN** the report names Woburn's old and new sub-region and the venues in Woburn, and the site's places are unchanged

#### Scenario: A faulty new version
- **WHEN** the file given has a town listed twice
- **THEN** the report names the fault, and the site's places are unchanged
