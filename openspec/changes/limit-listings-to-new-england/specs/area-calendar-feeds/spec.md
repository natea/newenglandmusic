## MODIFIED Requirements

### Requirement: A calendar feed for any area
`/calendar.ics` SHALL return an iCalendar document (`text/calendar; charset=utf-8`) of approved events at New England venues. It SHALL take the `region`, `state` and `metro` parameters with the same values and matching rules as the events listing, and filters given together SHALL all apply. With no parameters, it SHALL include events in every New England area.

The feed SHALL use only its own parameters, never the remembered filter cookie, and SHALL NOT set or change that cookie. Unknown or mismatched values SHALL be dropped as the listing drops them, so a stale URL covers a wider area rather than failing.

#### Scenario: State feed
- **WHEN** a calendar app fetches `/calendar.ics?state=vermont`
- **THEN** the feed holds the upcoming approved events at Vermont venues, and no others

#### Scenario: Metro feed
- **WHEN** a calendar app fetches `/calendar.ics?metro=ma-boston`
- **THEN** the feed holds events at venues in the Boston metro area's counties and cities

#### Scenario: Whole Northeast
- **WHEN** a calendar app fetches `/calendar.ics`
- **THEN** the feed holds upcoming approved events at New England venues, and none at venues elsewhere

#### Scenario: Remembered filter ignored
- **WHEN** a browser whose remembered filter is Maine fetches `/calendar.ics?state=vermont`
- **THEN** the feed is Vermont's, and the response sets no filter cookie

#### Scenario: Unknown area
- **WHEN** a feed URL names `state=atlantis`
- **THEN** the feed includes every New England area, with status 200
