## ADDED Requirements

### Requirement: Visitors can narrow chosen towns to some of their neighborhoods
Once one or more towns are chosen in the town filter, the filter SHALL offer the neighborhoods of those towns' venues, by neighborhood and town, in alphabetical order, as removable chips like the towns. A plain multi-select SHALL be offered without JavaScript. The `neighborhood` URL parameter SHALL name a chosen neighborhood as "<neighborhood>, <town>, <state code>", and MAY be repeated. When neighborhoods are chosen, the listing, the calendar's event dates, the day maps and the calendar feeds SHALL include only events at venues in those neighborhoods. A neighborhood outside the chosen towns, or unknown, SHALL be ignored. Without a chosen town, `neighborhood` SHALL be ignored. Chosen neighborhoods SHALL be remembered with the rest of the filter, and kept in the month links. Choosing no neighborhood SHALL mean the whole of the chosen towns.

#### Scenario: Two neighborhoods
- **WHEN** a visitor has chosen Boston, MA in the Boston Metro Region, and picks "West End" and "Allston"
- **THEN** only events at venues in those neighborhoods are listed, and both show as chips

#### Scenario: No town chosen
- **WHEN** a visitor opens `/?metro=ma-boston-metro-region&neighborhood=West End, Boston, MA`
- **THEN** the neighborhood is ignored, and the whole metro is listed

#### Scenario: Neighborhood from another town
- **WHEN** a visitor has chosen Cambridge, MA and the URL names "West End, Boston, MA"
- **THEN** it's ignored, and all of Cambridge is listed
