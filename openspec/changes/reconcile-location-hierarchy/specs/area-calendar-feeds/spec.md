# Spec Delta

## ADDED Requirements

### Requirement: Feeds follow the list of places
`/calendar.ics` SHALL take the `subregion` parameter, and `region` values from the list of places, with the same values and placement as the events listing. A feed address with an old `metro` value SHALL keep working as the listing reads it: as the sub-region that took over the address, or else as that metro's state. The subscribe links on the listing SHALL use the new parameters.

#### Scenario: Sub-region feed
- **WHEN** a calendar app fetches `/calendar.ics?subregion=ma-north-of-the-charles`
- **THEN** the feed holds events at venues placed in North of the Charles

#### Scenario: Region feed
- **WHEN** a calendar app fetches `/calendar.ics?region=nh-seacoast`
- **THEN** the feed holds events at venues placed in Seacoast's sub-regions

#### Scenario: A feed subscribed before the change
- **WHEN** a calendar app fetches `/calendar.ics?metro=ma-north-of-the-charles&town=Somerville, MA`
- **THEN** the feed holds only events at venues matched to Somerville

#### Scenario: Another state's old metro feed
- **WHEN** a calendar app fetches `/calendar.ics?metro=vt-north`
- **THEN** the feed holds Vermont's events, and no others

#### Scenario: Subscribe link
- **WHEN** a visitor has chosen the sub-region Portsmouth Area on the listing
- **THEN** the subscribe link's address uses `subregion=nh-portsmouth-area`
