# Spec Delta

## Purpose

Gives each New England venue one place in the site's list of places: its town, its listed neighborhood where the town has them, and so its sub-region and region. The placement is stored, so filters, pages and exports all read the same answer.

## ADDED Requirements

### Requirement: A venue is matched to a town in the list
A venue in a New England state SHALL be matched to the town of that state whose name, or one of whose other names, equals the venue's town text, ignoring case, surrounding whitespace, and the difference between hyphens and spaces. A venue outside New England, or with no town text, SHALL have no matched town.

#### Scenario: The town's own name
- **WHEN** a venue's state is MA and its town text is "somerville"
- **THEN** its matched town is Somerville, MA

#### Scenario: A village name
- **WHEN** a venue's state is MA and its town text is "Florence"
- **THEN** its matched town is Northampton, MA

#### Scenario: The same name in another state
- **WHEN** a venue's state is VT and its town text is "Burlington"
- **THEN** its matched town is Burlington, VT, not Burlington, MA

#### Scenario: Hyphens
- **WHEN** a venue's town text is "Manchester by the Sea" and the list has "Manchester-by-the-Sea"
- **THEN** its matched town is Manchester-by-the-Sea, MA

#### Scenario: A town the list doesn't know
- **WHEN** a Massachusetts venue's town text is "Bostn"
- **THEN** it has no matched town

### Requirement: A venue in a town with listed neighborhoods is matched to one
When a venue's matched town has listed neighborhoods, the venue SHALL be matched to the listed neighborhood that its town text names, or else the one whose name or other name equals the venue's neighborhood, ignoring case. A venue that matches none SHALL have no listed neighborhood. The venue's own neighborhood, from OpenStreetMap or an editor, SHALL NOT be changed by the match.

#### Scenario: Matched by the OpenStreetMap name
- **WHEN** a Boston venue's neighborhood is "Fenway-Kenmore", another name for the listed neighborhood Fenway
- **THEN** its listed neighborhood is Fenway, and its own neighborhood still reads "Fenway-Kenmore"

#### Scenario: Matched by its town text
- **WHEN** a venue's town text is "Jamaica Plain", another name for Boston and its neighborhood Jamaica Plain
- **THEN** its matched town is Boston and its listed neighborhood is Jamaica Plain

#### Scenario: A neighborhood the list doesn't name
- **WHEN** a Boston venue's neighborhood is "Chinatown", which no listed neighborhood names
- **THEN** it has no listed neighborhood

### Requirement: A placed venue is in exactly one sub-region and region
A venue with a matched town SHALL be in one sub-region: its listed neighborhood's, or else its town's. Its region and state SHALL be that sub-region's. A venue with no matched town SHALL be in no sub-region and no region, and SHALL still belong to its state.

#### Scenario: By town
- **WHEN** a venue's matched town is Woburn, which the list puts in Merrimack Valley / Greater Lowell
- **THEN** the venue is in that sub-region and its region, Northeast Massachusetts, and in no other

#### Scenario: By listed neighborhood
- **WHEN** a Boston venue's listed neighborhood is Jamaica Plain
- **THEN** the venue is in the sub-region Boston Neighborhoods

#### Scenario: Boston with no listed neighborhood
- **WHEN** a Boston venue has no listed neighborhood
- **THEN** the venue is in the sub-region of Boston's own row, Downtown & Central Boston

#### Scenario: Unplaced
- **WHEN** a Massachusetts venue has no matched town
- **THEN** it is in no sub-region or region, and a filter for the state Massachusetts still includes it

### Requirement: Placement follows changes to the venue and to the list
A venue's placement SHALL be worked out again when its state, town text or neighborhood changes, by an editor, the sheet sync or the neighborhood lookup, and for every venue whenever the list of places is loaded. Working it out again SHALL NOT re-render the stored HTML of the venue's events.

#### Scenario: The neighborhood lookup finds a neighborhood
- **WHEN** `lookup_venue_neighborhoods` gives a Boston venue the neighborhood "South Boston"
- **THEN** the venue moves to the sub-region East Boston, Charlestown & South Boston

#### Scenario: An editor corrects the town text
- **WHEN** an editor changes a venue's town text from "Bostn" to "Boston"
- **THEN** the venue is placed in Boston

#### Scenario: The list moves a town
- **WHEN** a new file moves Woburn to another sub-region and is loaded
- **THEN** Woburn's venues are in the new sub-region

#### Scenario: Events left alone
- **WHEN** a venue's placement changes
- **THEN** the stored HTML of its events is unchanged

### Requirement: Editors can see and correct a venue's placement
The venue admin SHALL show a venue's matched town, listed neighborhood, sub-region and region, and whether an editor set them. An editor SHALL be able to choose the town, and a listed neighborhood of it, by hand. A hand-set placement SHALL be kept when placement is worked out again, until the editor clears it. The venue list SHALL have a filter for New England venues with no matched town.

#### Scenario: An editor chooses the town
- **WHEN** an editor sets the matched town of a venue whose town text is "Shelburne Falls" to Buckland, MA
- **THEN** the venue is in Buckland's sub-region, and later sheet syncs and loads leave it there

#### Scenario: Clearing a hand-set town
- **WHEN** the editor clears the hand-set town
- **THEN** the venue is matched by its town text again

#### Scenario: Finding unplaced venues
- **WHEN** an editor filters the venue list to venues with no matched town
- **THEN** only New England venues with no matched town are listed

### Requirement: Unplaced venues are reported
`report_unplaced_venues` SHALL list each active New England venue with no matched town, and each venue whose matched town has listed neighborhoods but which has none, with its name, state, town text and neighborhood, so editors can fix the venue or add another name. Each load of the list SHALL record the number of venues placed and unplaced.

#### Scenario: A venue with an unknown town
- **WHEN** an active Rhode Island venue's town text is "Chepachet" and no town or other name matches it
- **THEN** the report lists the venue with "Chepachet, RI"

#### Scenario: A Boston venue with an unlisted neighborhood
- **WHEN** a Boston venue's neighborhood is "Chinatown"
- **THEN** the report lists it among the venues with no listed neighborhood

#### Scenario: Inactive venues
- **WHEN** an inactive venue has no matched town
- **THEN** the report doesn't list it

### Requirement: What a venue shows is unchanged
A venue's events, pages and exports SHALL keep showing the venue's own town text and neighborhood. Placement SHALL NOT replace them with the matched town's name or the listed neighborhood's.

#### Scenario: A venue that gives a neighborhood as its town
- **WHEN** a venue's town text is "Allston" and its matched town is Boston
- **THEN** its events still read "Allston, MA"
