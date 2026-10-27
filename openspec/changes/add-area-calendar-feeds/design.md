## Context

- **The area filter already exists.**
  - `core/geo_filters.py`'s `parse_geo_filter(querydict)` resolves `region`, `state` and `metro` slugs to `GeoArea`s.
  - Unknown or mismatched slugs are dropped.
  - `GeoFilter.q(prefix=...)` filters events by venue.
  - `GeoFilter.query_string` rebuilds the parameters.
- **The single-event download already exists.** `core/views/event_ics_download.py` builds one event with `core/utils.get_ics_string_from_event`, using `icalendar`. It sets `UID` to `uuid4()` on every download, and `DTEND` to the start plus an hour.
- **Event data:**
  - `Event.calendar_name` gives "<title and artists> [New England Music]", and `venue_name_and_address` the location.
  - `Event.objects` is approved events only, and events have `is_cancelled`.
  - The model has no updated-at field, only `created_at`.

## Goals / Non-Goals

**Goals:**
- Feeds that calendar apps can subscribe to and refresh without duplicating events.
- The same area definitions and URL values as the listing.

**Non-Goals:**
- Feeds by genre, venue or artist (later, as more parameters on the same URL).
- Per-visitor feeds, such as saved shows (see `add-saved-shows`), and authentication.
- City or neighborhood areas finer than the sheet's metro areas.

## Decisions

**1. One URL, with the listing's parameters.**
- **The URL:** `/calendar.ics?region=…&state=…&metro=…`, rather than a path per area like `/feeds/state/vermont.ics`.
- **Why:**
  - The subscribe link is built from the existing `geo_filter.query_string`.
  - Combinations work for free, for example a region and a metro together.
  - Genre, venue and artist can later be added as more parameters, without new routes.
- **What it reads:** the view calls `parse_geo_filter(request.GET)` directly, not `geo_filter_for_request`. So the cookie is never read or written.

**2. Stable UIDs, shared with the single-event download.**
- **The UID:** `event-<pk>@<site host>`, with the host taken from `SITE_URL`.
- **One builder:** a function `event_to_ical(event)` in `core/calendar_feeds.py` builds a `VEVENT` with:
  - `UID`;
  - `DTSTART`, and `DTEND` an hour later;
  - `DTSTAMP`, `SUMMARY`, `LOCATION` and `DESCRIPTION`;
  - `URL`, the event's `/event/<id>` link;
  - `STATUS:CANCELLED` when the event is cancelled.
- **The download:** `get_ics_string_from_event` becomes a thin wrapper around it, so a downloaded event and its feed copy share a UID.
- **Change detection:** with no updated-at field, `SEQUENCE` is left out. Calendar apps compare the event's contents on refresh, which Google, Apple and Outlook all do for subscribed calendars.

**3. The window and size.**
- **Which events:** `Event.objects` with a start from 7 days ago up to 90 days ahead, filtered by `geo_filter.q(prefix="venue__")`, with `select_related("venue")`, ordered by start time.
- **Why 7 days back:** an app refreshing mid-week still shows the weekend's shows.
- **Why 90 days ahead:** it bounds the size. The whole Northeast is roughly 2,000 events, around 1 MB.

**4. Calendar properties.**
- **Name:** `X-WR-CALNAME` is "New England Music", plus ": <area labels joined by " / ">" when an area is chosen.
- **Description and time zone:** `X-WR-CALDESC` is a sentence linking the site, and `X-WR-TIMEZONE` is America/New_York.
- **Refresh:** `REFRESH-INTERVAL;VALUE=DURATION:PT6H` and `X-PUBLISHED-TTL:PT6H`. Many apps ignore these and use their own schedule, about every 8 to 24 hours for Google, but Apple Calendar honours them.

**5. Caching.**
- **The ETag:** a SHA-1 hash of the feed's bytes.
- **Headers:** `Cache-Control: public, max-age=3600`, so a CDN or the app may reuse the feed for an hour.
- **Conditional requests:** a matching `If-None-Match` gets a 304.
- **Why build it each time:** the feed is built on every request, which takes tens of milliseconds for a few thousand events, so no server cache is needed yet.

**6. Subscribe links.**
- **Where:** a snippet, `core/templates/core/calendar_subscribe.html`, included after the filter form on the homepage and month archive.
- **What it builds:** from `request.build_absolute_uri` and `geo_filter.query_string`:
  - the `webcal://` link, which is the `https://` URL with the scheme swapped;
  - a Google Calendar link, `https://calendar.google.com/calendar/r?cid=<webcal URL, encoded>`;
  - the plain URL, in a read-only text field to copy.
- **Without JavaScript:** it all works without it. A "copy" button can be a later touch.

**How it's tested.** No outside service is involved.
- **The feed:** Django tests fetch `/calendar.ics` with the test client, parse it with `icalendar.Calendar.from_ical`, and check:
  - which events are included: area, window, approval;
  - the UIDs against the single-event download;
  - cancellation, the calendar name and refresh properties;
  - the ETag and 304, and that the cookie is ignored.
- **The subscribe links:** render tests check the links for a chosen area and for none.
- **Areas:** the existing `core/tests/geo_fixture.py` provides them.

## Risks / Trade-offs

- **[Apps refresh on their own schedule]** → Google can take up to a day to show a new show. That's documented in the subscribe note, and the site's listing remains the up-to-date view.
- **[Feed size for the whole Northeast]** → The 90-day window bounds it, and ETag and caching make refetches cheap. If needed, a later change can add a CDN or shorten the window for the all-areas feed.
- **[Changing the single-event UID]** → An event already downloaded with a random UID, then seen again in a feed, appears twice once. That only affects events downloaded before this change, and those pass within weeks.

## Migration Plan

Deploy. No data changes and no re-rendering are needed: the subscribe snippet sits in the page templates, not the stored event HTML.

**Rollback:** revert. Subscribed calendars then stop updating, and keep their last copy.
