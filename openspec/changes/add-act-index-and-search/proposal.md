## Why

Every live band and artist has a page, but the only way to reach one is a performer link in an event listing, so an act with no upcoming show (most of Sooz's vetted Oh Hello Boston acts, and every act between tours) is reachable only by typing its address. Those pages are also marked `noindex` and left out of the sitemap, so search engines can't find them either. A local band's page with its bio, members and links is worth finding whether or not a show is booked.

## What Changes

- **An A–Z index of bands and artists** at `/bands`, in the site's index-card style: a letter rail (A–Z and #), and under each letter every live band and artist, with its kind, home town and state, and the date of its next show when it has one. Each name links to its page. `/artists` redirects to it. Acts held for review aren't listed. The site's menu gains "Bands & artists".
- **Search finds acts.** A search (`?s=`) lists the bands and artists whose names match, above the shows and pages it already finds, each linking to its page with its kind and town.
- **No `noindex` on band and artist pages.** Every live act's page may be indexed, show or no show, and the sitemap lists every live act's page and the index. Held acts stay out of both, as they have no page.
- **Not in this change:** filtering the public index by source (the admin's source filter already shows Sooz's acts); filtering by genre or state; venue pages.

## Capabilities

### New Capabilities
- `act-index`: the public A–Z index of bands and artists, and acts in search results.

### Modified Capabilities
- `band-pages`: band and artist pages are indexable and listed in the sitemap whether or not the act has an upcoming show.

## Impact

- **Code:** a new `core/views/act_index.py` and `core/templates/core/act_index.html` (reusing the band page's card and tab styles); `core/views/search.py` and `core/templates/core/search.html` (an acts section); `core/views/act_page.py` and `band.html` (no `noindex`); `core/sitemap.py` (every live act, and `/bands`); the menu item (a `MenuItem` row, through a data migration, or the admin).
- **Depends on** `import-curated-act-lists` for `needs_review` (held acts are left out); builds on its branch.
- **No new data or API.** About 3,100 acts today; the index is one query, ordered by name.
