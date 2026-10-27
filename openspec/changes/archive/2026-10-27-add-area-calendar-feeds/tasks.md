## 1. Shared event builder

- [x] 1.1 Add `core/calendar_feeds.py` with `event_uid(event)` (`event-<pk>@newenglandmusic`, fixed so a domain change doesn't change UIDs) and `event_to_ical(event)`. It sets `UID`, `DTSTART`, `DTEND` (an hour later), `DTSTAMP`, `SUMMARY`, `LOCATION` and `DESCRIPTION` (tags stripped), `URL` (the event's `/event/<id>`), and `STATUS:CANCELLED` when cancelled. Make `core/utils.get_ics_string_from_event` use it. Verify with 1.2.
- [x] 1.2 Add tests for the builder and for the single-event download: the same UID on repeated downloads, `STATUS:CANCELLED`, `URL`, and the existing `core/tests/test_event_calendar_links.py` still passing. Verify that they pass.

## 2. Feed view

- [x] 2.1 Add the `/calendar.ics` view and URL. It:
  - parses the area with `parse_geo_filter(request.GET)`, without the cookie;
  - takes events from `Event.objects` starting from 7 days ago up to 90 days ahead, in the area, with `select_related("venue")`, in start-time order;
  - builds the calendar, with `X-WR-CALNAME` ("New England Music" plus the area labels), `X-WR-CALDESC`, `X-WR-TIMEZONE`, `REFRESH-INTERVAL` and `X-PUBLISHED-TTL` (PT6H);
  - responds as `text/calendar; charset=utf-8` with an `ETag` (a SHA-1 of the body) and `Cache-Control: public, max-age=3600`, or 304 on a matching `If-None-Match`.

  Verify with 2.2.
- [x] 2.2 Add `core/tests/test_calendar_feeds.py`, which parses responses with `icalendar` and uses `geo_fixture`. It covers every feed scenario in the spec:
  - a state, a metro and the whole Northeast;
  - the remembered filter ignored, with no cookie set;
  - an unknown area;
  - stable identifiers, a cancelled event, the window, an unapproved event left out, and the calendar name;
  - an unchanged feed's 304, and a changed feed's new ETag.

  Verify that it passes.

## 3. Subscribe links

- [x] 3.1 Add `core/templates/core/calendar_subscribe.html`: "Subscribe to this calendar", with a `webcal://` link, a Google Calendar link (`calendar.google.com/calendar/r?cid=<encoded webcal URL>`) and a read-only field holding the `https://` URL. It's built from `geo_filter.query_string`, and includes a note that apps refresh on their own schedule. Include it after the filter form on the homepage and month archive, and style it in `geo_filter.scss`. Verify with 3.2.
- [x] 3.2 Add render tests: subscribing to a state (all three links for `state=vermont`) and with nothing chosen (no parameters), on the homepage and a month archive page. Verify that they pass.

## 4. Docs and check

- [x] 4.1 Document `/calendar.ics` and its parameters in `PRODUCTION.md`, and in `AGENTS.md`'s overview if it lists the site's pages. Verify by reading.
- [x] 4.2 Run the whole suite with outbound network blocked. Then subscribe to a local feed in a real calendar app, or import it, through `http://127.0.0.1:8001/calendar.ics?state=vermont`, and check the events, their times and the calendar name. Verify that the tests pass and the feed imports cleanly.
  - 2026-10-27: subscribed in Apple Calendar to `http://localhost:8001/calendar.ics?state=vermont`. The `webcal://` link failed locally: Calendar fetches `webcal://` over HTTPS, which the dev server doesn't serve. On Render, which serves HTTPS, the `webcal://` link works as built.
