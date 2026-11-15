Issue: [#15 Incorporate the Google Calendar Simple API to generate calendars that people can subscribe to](https://github.com/natea/newenglandmusic/issues/15)

## Why

The site already publishes live calendar feeds by area (`/calendar.ics`), and calendar apps re-check them every few hours, so subscribers keep getting new and changed shows. But the option to subscribe is tucked into a collapsed line ("Subscribe to this calendar") under the area filter, and a venue's page has no way to subscribe at all. People who would subscribe never find it. The asker (issue 15) chose to start here: make the existing subscribe option easy to find, near the top of the listing and on each venue's page, before building anything that needs a Google sign-in.

## What Changes

- **A visible Subscribe button near the top of the listing** (homepage and month archive pages), replacing the collapsed line under the area filter. It offers what the line offered, for the same area: the Apple Calendar, Outlook or phone link, the Google Calendar link, and the address to copy, plus a note (already in the page's panel, now in the spec) that Google can take up to a day. The button names the area chosen. It still works without JavaScript, and keeps the `calendarLink` and `google` link classes, so the existing subscribe analytics event keeps firing.
- **The same Subscribe button on each venue's page**, for the feed of the area the venue is in (its state), labelled with that area ("Subscribe: Massachusetts"), the same label form as the listing.
- **No change to the feeds.** Their content, identifiers, refresh hints and caching stay as they are. Narrower calendars (one venue, artist or genre), personal calendars of picked shows, and Google sign-in (adding shows to someone's own Google Calendar, free-time suggestions, friend circles) are left for later changes. The Google Calendar Simple API library is not used: it needs people to grant Google access, which this change does not ask for.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `area-calendar-feeds`: the listing's subscribe option becomes a visible button near the top of the page.
- `venue-pages`: a venue's page offers the same button, for its state's feed. (This capability is introduced by `add-venue-pages`, which is not yet archived; this change must be archived after it.)

## Impact

- **Templates and styles:** `core/templates/core/calendar_subscribe.html` (reworked into a button and panel), `core/templates/core/index.html` (moved up), the venue page template from `add-venue-pages`, and the stylesheet that styles it now (`core/static/core/scss/geo_filter.scss`), `core/tests/test_calendar_feeds.py` (two assertions on the old wording), and the `PRODUCTION.md` paragraph describing the old panel under the area filter.
- **Code:** `subscribe_links` in `core/calendar_feeds.py` is reused unchanged. The venue page view builds the `GeoFilter` it takes from the venue's state (see the design, decision 3). No model, migration, feed or URL change.
- **Analytics:** no new event unless the owner asks (see the design's open questions). The existing `calendar_feed_subscribed` event fires on `a.calendarLink` (`core/static/core/js/analytics.js`), so the markup keeps those classes; venue-page clicks count in the same event.
- **No new data source, API, key or paid call.** Screens change, so this needs a design round.
