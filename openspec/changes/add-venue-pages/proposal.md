## Why

The site keeps about 730 editor-curated venues, with facts no show app has (what a room books, whether it takes new acts and how to ask, its size, age and access notes), but a visitor can't see any of it: venues exist only as a bold name in listings. Fans want to know what's on at a room they like; musicians want to know whether it books acts like theirs and how to ask. Both are this product's audiences (PRODUCT.md), and a venue page serves both.

## What Changes

- **Venue pages.** Each active venue gets a public page at `/venues/<slug>`, designed as the room's own show bill (the "gig-poster column" chosen in the design round, sketched in `.impeccable/mocks/decision/poster-column.html`):
  - the venue's name on the plum tab;
  - one fact line: kind and size of room, neighborhood, town and state, a "Map ↗" link out to Google Maps, and what it books; ending in an "Open booking" link when the venue takes new acts;
  - "The bill": every upcoming approved show, night by night, with a big tabular day number, the headliner bold and larger, openers after "with", the time, and today's nights marked; each night links to its event page;
  - below the bill, "Playing here" (booking type, link and notes, open mic, genres and niche, size) and "Getting here" (address text, age policy, accessibility notes, family- and LGBTQ+-friendly, the venue's website), each field shown only when known.
- **No embedded map.** Location is text plus a link out to Google Maps; the Google Places display terms are unsettled, so the page draws no map from Google-derived coordinates.
- **Venue slugs.** `Venue` gains a unique `slug` (a migration fills it from the name, with the town added when two venues share a name). The sheet sync never touches it.
- **Who links to it:** the event page's venue name, and the admin's "View on site". Listings keep one link per row (`event-listing`, in `add-event-pages`).
- **Inactive and empty venues:** a venue marked inactive in the sheet answers 404; an active venue with no upcoming shows still has a page, saying so.
- **Search engines:** venue pages are `noindex` while the site is unshared, and stay out of the sitemap in this change.

## Capabilities

### New Capabilities
- `venue-pages`: the public page for one venue: its address, what it shows for fans and for musicians, its bill of upcoming shows, how it is linked, and how it reads on phones.

### Modified Capabilities
<!-- none: the event page's venue link is specified here, since event-pages is not yet archived -->

## Impact

- **Model and migration:** `Venue.slug`, filled for existing venues; `core/sheet_sync` leaves it alone (it is not a sheet column).
- **Code:** a new `core/views/venue_page.py`, `core/templates/core/venue.html` and `core/static/core/scss/venue.scss` (reusing the card partial from `add-event-pages`); the headliner and openers come from `billing()` in `core/artist_names.py` (also from `add-event-pages`); `Venue.get_absolute_url`; the event page links its venue.
- **Order:** builds after `add-event-pages`, whose `billing()`, card partial and event page this uses. Built first, it would introduce `billing()` and the card partial itself.
- **No new data source, API or paid call.** Everything shown is already in the venue record and its approved events. Nothing from Google Places is displayed beyond the map link, which opens Google's own page.
