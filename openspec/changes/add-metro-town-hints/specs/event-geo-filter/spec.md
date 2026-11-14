## ADDED Requirements

### Requirement: The chosen metro area shows what it covers
When a metro area is chosen, the filter SHALL show, under the Metro Area menu, what it covers: for a Massachusetts sub-region, the towns (or, for Boston's sub-regions, the neighborhoods) the editors listed, in their words; for another metro, its counties, or else its towns. It SHALL be rendered by the server, so it shows without JavaScript, on the listing and the discovery deck alike. With no metro chosen, nothing SHALL be shown. Each Metro Area option SHALL carry the same text as its tooltip (`title`).

#### Scenario: A sub-region's towns
- **WHEN** a visitor opens `/?metro=ma-inner-west-suburbs`
- **THEN** a line under the Metro Area menu reads "Covers: Brookline, Newton, Watertown, Arlington, Belmont, Waltham"

#### Scenario: A Boston sub-region's neighborhoods
- **WHEN** a visitor opens `/?metro=ma-downtown-central-boston`
- **THEN** the line reads "Covers: Back Bay, Beacon Hill, South End, North End, Fenway, Downtown, West End"

#### Scenario: A metro matched by county
- **WHEN** a visitor opens `/?metro=nh-south`
- **THEN** the line names its counties, ending "… Strafford and Sullivan counties"

#### Scenario: No metro chosen
- **WHEN** a visitor opens `/?state=massachusetts`
- **THEN** no covers line is shown

#### Scenario: Tooltips on the options
- **WHEN** the Metro Area menu is shown
- **THEN** the "North of the Charles" option's `title` is "Covers: Cambridge, Somerville, Medford, Malden, Everett, Chelsea, Revere, Winthrop"

#### Scenario: The discovery deck
- **WHEN** a visitor opens `/discover?metro=ma-inner-west-suburbs`
- **THEN** the same covers line is shown under its Metro Area menu

#### Scenario: The editors' words stay in step with the matching
- **WHEN** the areas are loaded
- **THEN** every town or neighborhood named in a sub-region's covers text is one its matching lists include
