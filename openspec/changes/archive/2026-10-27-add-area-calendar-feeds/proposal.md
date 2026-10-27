## Why

Visitors who follow the music in their area have to keep coming back to the site to see what's new. A calendar feed they subscribe to once puts every show in their region, state or metro area straight into Google Calendar, Apple Calendar or Outlook, and keeps it up to date.

## What Changes

- **A feed for any area:** `/calendar.ics` serves an iCalendar feed of upcoming approved events.
  - It takes the same `region`, `state` and `metro` parameters as the listing. For example, `/calendar.ics?state=vermont` or `/calendar.ics?metro=ma-boston`.
  - With no parameters, it covers the whole Northeast.
  - It reads only its own URL, never the visitor's remembered filter, so a subscribed feed stays the area it was made for.
- **"Neighborhood" means metro area.** The venue sheet's finest areas are its metro areas, such as "MA: Boston" or "MA: Cape Cod". A city or neighborhood level would come from the sheet first.
- **A "Subscribe to this calendar" link beside the area filter.**
  - It's for whichever area is chosen.
  - On a phone or a Mac, a `webcal://` link opens the calendar app.
  - A plain link to copy, and a Google Calendar "add by URL" link, cover the rest.
- **Feeds that update rather than duplicate:**
  - **Stable IDs:** each event gets a lasting identifier, so a calendar app that refreshes the feed updates events in place, and removes ones that are deleted.
  - **Cancelled events** are marked cancelled.
  - **The window:** shows from the past week through the next 90 days.
  - **Refresh:** the feed asks calendar apps to refresh every six hours.
- **The single-event ICAL download** gets a stable identifier too. It currently makes a new random one each time, so adding an event by hand and then subscribing to its area would show it twice.
- **Not included:** feeds by genre, venue or artist. The feed's URL takes listing parameters, so those can be added later as new parameters.

## Capabilities

### New Capabilities
- `area-calendar-feeds`: iCalendar feeds of upcoming events for any region, state or metro area (or all of them), their contents and refresh behavior, and the subscribe links.

### Modified Capabilities
None. `event-geo-filter`'s areas and URL values are reused as they are, and no spec covers the single-event download, so making its identifier stable needs no spec change.

## Impact

- **New code:**
  - a `/calendar.ics` view;
  - a shared event-to-iCalendar function, used by the feed and the single-event download;
  - a subscribe snippet beside `geo_filter_form.html`.
- **Dependencies:** none. It uses `icalendar`, which is already pinned.
- **Load:** calendar apps fetch feeds every few hours. A feed of the whole Northeast is about 2,000 events, roughly 1 MB. Responses carry `Cache-Control` and an `ETag`, so unchanged feeds cost little.
- **Tests:** Django tests on the parsed feed, with no outside services.
