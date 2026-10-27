## Purpose

Lets visitors subscribe, in their own calendar app, to the shows in any region, state or metro area, so new and changed shows reach their calendar without visiting the site.

## ADDED Requirements

### Requirement: A calendar feed for any area
`/calendar.ics` SHALL return an iCalendar document (`text/calendar; charset=utf-8`) of approved events. It SHALL take the `region`, `state` and `metro` parameters with the same values and matching rules as the events listing, and filters given together SHALL all apply. With no parameters, it SHALL include events in every area.

The feed SHALL use only its own parameters, never the remembered filter cookie, and SHALL NOT set or change that cookie. Unknown or mismatched values SHALL be dropped as the listing drops them, so a stale URL covers a wider area rather than failing.

#### Scenario: State feed
- **WHEN** a calendar app fetches `/calendar.ics?state=vermont`
- **THEN** the feed holds the upcoming approved events at Vermont venues, and no others

#### Scenario: Metro feed
- **WHEN** a calendar app fetches `/calendar.ics?metro=ma-boston`
- **THEN** the feed holds events at venues in the Boston metro area's counties and cities

#### Scenario: Whole Northeast
- **WHEN** a calendar app fetches `/calendar.ics`
- **THEN** the feed holds upcoming approved events in every area

#### Scenario: Remembered filter ignored
- **WHEN** a browser whose remembered filter is Maine fetches `/calendar.ics?state=vermont`
- **THEN** the feed is Vermont's, and the response sets no filter cookie

#### Scenario: Unknown area
- **WHEN** a feed URL names `state=atlantis`
- **THEN** the feed includes every area, with status 200

### Requirement: Feed events stay up to date in calendar apps
Each event in a feed SHALL have:
- a UID that stays the same for that event across every feed and download;
- its start time, and an end an hour later, as the single-event download has;
- its name, venue and address, and description;
- a link to the event on the site.

A cancelled event SHALL have `STATUS:CANCELLED`. The feed SHALL include events that started up to 7 days ago, through those starting within the next 90 days, in start-time order.

The calendar SHALL be named for the site and the area, such as "New England Music: Vermont", and SHALL ask to be refreshed every six hours (`REFRESH-INTERVAL` and `X-PUBLISHED-TTL`).

The site's name in the calendar's name, and the part of each UID after "@", SHALL come from the `SITE_NAME` and `UID_DOMAIN` settings, which default to "New England Music" and "newenglandmusic".

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
- **THEN** the calendar is named "New England Music: MA: Cape Cod", and asks to be refreshed every six hours

### Requirement: Feeds are cheap to refetch
A feed response SHALL carry an `ETag` computed from its content, and `Cache-Control: public, max-age=3600`. A request whose `If-None-Match` matches the ETag SHALL get a 304 with no body.

#### Scenario: Unchanged feed
- **WHEN** a calendar app refetches a feed with the ETag it was given, and nothing has changed
- **THEN** the response is 304, with no body

#### Scenario: Changed feed
- **WHEN** an event in the area is added after the ETag was given
- **THEN** the refetch gets 200, with the new event and a new ETag

### Requirement: Visitors can subscribe from the listing
Beside the area filter, the homepage and month archive pages SHALL offer "Subscribe to this calendar" for the area chosen, or for all areas when none is chosen. It SHALL offer:
- a `webcal://` link to the feed;
- a link that adds the feed in Google Calendar by URL;
- the feed's `https://` URL to copy.

It SHALL work without JavaScript.

#### Scenario: Subscribe to a state
- **WHEN** a visitor has Vermont chosen
- **THEN** the subscribe links point at `/calendar.ics?state=vermont`, with `webcal://` for the app link, and the Google Calendar link adds that URL

#### Scenario: Nothing chosen
- **WHEN** no area is chosen
- **THEN** the subscribe links point at `/calendar.ics`, with no parameters
