# Proposal

## Why

The sitemap lists only the home page and one archive page per month, because those are the only pages the site has. People search for a venue ("Paradise Rock Club shows"), a show, or a place ("live music in Vermont"), and the site has no page that answers any of those. Each event's share link (`/event/<id>`) only redirects to its month page, and the region, state and metro filters exist only as query strings. A sitemap is only as useful as the pages behind it, so this change adds those pages and lists them.

## What Changes

The change is planned and built in four parts, which can be released one at a time.

1. **Venue pages.** Each active venue gets a page at `/venue/<slug>/`, with its name, town and state, the facts we keep about it, a link to it on Google Maps, and its upcoming shows. The venue name in event listings links to it.
2. **Event pages.** `/event/<id>` becomes a real page, with the show's time, venue, artists, price, age policy, description, and ticket and calendar links. Today it only redirects to the month page. Share links keep their URL and their preview tags.
3. **Area pages.** Each region, state and metro area that the filters offer gets a page: `/region/<slug>/`, `/state/<slug>/` and `/metro/<slug>/`. Each lists that area's upcoming shows, like the filtered home page, but at a stable address with its own title. It doesn't use or set the remembered-filter cookie.
4. **A better sitemap.**
   - It lists the venue, event and area pages as well.
   - Its entries are in a stable, sorted order.
   - Pages carry a last-modified date where we know one.
   - A `robots.txt` names the sitemap. Search engines are told not to index the site until a launch setting allows it, since the site stays unshared until the Google Places terms are met.

## Capabilities

### New Capabilities

- `venue-pages`: a public page per active venue, and the links to it.
- `event-pages`: a public page per approved event at its share link.
- `area-pages`: a public page per region, state and metro area the filters offer.
- `sitemap`: what the sitemap and `robots.txt` list, their order and dates, and when search engines may index the site.

### Modified Capabilities

None. The listing filters keep their query strings and cookie, as `event-geo-filter` describes; area pages are other pages, and that spec already says the cookie doesn't affect them.

## Impact

- **Models and migrations:**
  - `Venue.slug`: unique, filled in for existing venues, and set for new venues the sheet sync creates.
  - `Event.updated_at` and `Venue.updated_at`, for last-modified dates. Code that changes them with `queryset.update()` has to set the date itself.
- **Views and URLs:** new views for venue, event and area pages, all routed ahead of the static-page catch-all. `event_redirect` is replaced by the event page.
- **Templates:**
  - new page templates
  - `event.html` links the venue name to its page, so stored event HTML is re-rendered with `resave_all_events`
- **Sitemap:** `core/sitemap.py` becomes several sitemap sections. There's a new `robots.txt` view, and a new `ALLOW_SEARCH_INDEXING` setting, off by default.
- **Google Places terms:** venue pages show only what we may keep: the sheet's details, plus a Google Maps link built from the place ID. They don't show the stored Places address, phone or website, which `refresh-place-coordinates` removes anyway. No map is embedded until the map decision is made.
- **Launch:** none of this makes the site public. `ALLOW_SEARCH_INDEXING` is turned on as part of launch, alongside the other launch checks in `PRODUCTION.md`.
