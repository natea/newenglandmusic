## ADDED Requirements

### Requirement: Visitors can narrow a metro area to some of its towns
Once a metro area is chosen, the filter SHALL offer the towns in it that have at least one venue, by the venues' town and state, in alphabetical order, as a multi-select. The `town` URL parameter SHALL name a chosen town as "<town>, <state code>", such as `town=Somerville, MA`, and MAY be repeated. When towns are chosen, the listing, the calendar's event dates, the day maps and the calendar feeds SHALL include only events at venues in those towns. A town outside the chosen metro, or unknown, SHALL be ignored. Choosing no town SHALL mean the whole metro. Without a metro, `town` SHALL be ignored. The chosen towns SHALL be kept in the remembered filter, and in the month links, like the other filters. The multi-select SHALL work without JavaScript. Changing the metro SHALL drop towns that aren't in the new one.

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
