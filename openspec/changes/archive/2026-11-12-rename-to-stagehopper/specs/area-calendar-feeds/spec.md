## MODIFIED Requirements

### Requirement: Feed events stay up to date in calendar apps
Each event in a feed SHALL have:
- a UID that stays the same for that event across every feed and download;
- its start time, and an end an hour later, as the single-event download has;
- its name, venue and address, and description;
- a link to the event on the site.

A cancelled event SHALL have `STATUS:CANCELLED`. The feed SHALL include events that started up to 7 days ago, through those starting within the next 90 days, in start-time order.

The calendar SHALL be named for the site and the area, such as "StageHopper: Vermont", and SHALL ask to be refreshed every six hours (`REFRESH-INTERVAL` and `X-PUBLISHED-TTL`).

The site's name in the calendar's name, and the part of each UID after "@", SHALL come from the `SITE_NAME` and `UID_DOMAIN` settings, which default to "StageHopper" and "stagehopper".

#### Scenario: Names from the settings
- **WHEN** `SITE_NAME` is "Boston Shows" and `UID_DOMAIN` is "boston-shows"
- **THEN** a Vermont feed's calendar is named "Boston Shows: Vermont", and event 12's UID is `event-12@boston-shows`

#### Scenario: Stable identifiers
- **WHEN** a feed is fetched twice, and the event's single-event download is fetched
- **THEN** the event has the same UID in all three

#### Scenario: Cancelled event
- **WHEN** an event in the feed is marked cancelled
- **THEN** the feed lists it with `STATUS:CANCELLED`

#### Scenario: Window
- **WHEN** events start 8 days ago, 2 days ago, in 30 days and in 120 days
- **THEN** the feed holds the events of 2 days ago and in 30 days only

#### Scenario: Unapproved event left out
- **WHEN** an event in the area awaits approval
- **THEN** it isn't in the feed

#### Scenario: Calendar name
- **WHEN** a calendar app fetches `/calendar.ics?metro=ma-cape-cod`
- **THEN** the calendar is named "StageHopper: MA: Cape Cod", and asks to be refreshed every six hours

#### Scenario: Default names

- **WHEN** a feed is fetched with `SITE_NAME` and `UID_DOMAIN` unset
- **THEN** a Vermont feed's calendar is named "StageHopper: Vermont", and event 12's UID is `event-12@stagehopper`
