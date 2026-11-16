Issue: [#58 Remove non-New England regions and states from the homepage search functionality](https://github.com/natea/newenglandmusic/issues/58)

## Why

The site is a discovery tool for New England artists and bands (Massachusetts, Connecticut, Rhode Island, New Hampshire, Maine and Vermont). Its search still offers the Chesapeake Bay, Mid-Atlantic and Tri-State regions and states from DC to Pennsylvania, and shows at venues in those places appear in the calendar. Issue #58 asks to remove them. The asker settled the scope for this first phase: no events in the listings calendar or search for cities outside New England.

## What Changes

- **Events outside New England are hidden.** An approved event whose venue is outside the six New England states no longer appears in the homepage and month listings, the calendar's dates and day maps, site search, the calendar feeds, saved shows, act and band pages (their show lists and next-show dates), the discover page or the sitemap's months. Issue #58 asked only for the calendar and search; the other pages are included so that hidden shows don't leak back through them, and the design lists this as a question for the owner. Event pages opened by direct link still work.
- **Search choices are trimmed.** The homepage's Region, State and Metro Area choices offer only areas wholly inside New England: the Chesapeake Bay, Mid-Atlantic and Tri-State regions, DC, Delaware, Maryland, New Jersey, New York and Pennsylvania, and the metro areas that belong to those states, are no longer offered.
- **Nothing is deleted.** Venues, events and areas stay in the database, so a later phase can bring them back by changing one list of states.
- **The admin opens on New England** *(revision, 2026-11-16)*. The event list, the review queue (`/admin/core/alleventproxy/`) and the venue list show New England's venues and events by default, with an "All areas" choice in the sidebar for the rest. Choosing a Region, State or Metro filter still shows that area, wherever it is. About 160 venues and 200 of the shows awaiting review were outside New England on 2026-11-15.
- **Events stop being fetched for venues outside New England** *(revision, 2026-11-16)*. `fetch_events` skips a venue whose state is set and isn't one of the six, so the daily job stops gathering shows the site never shows and the review queue stops refilling with them. A venue with no state is still fetched (fixing its state brings its shows straight in), and `--sheet-ids` still fetches any venue it names. Existing events stay until they pass.
- **Stale links.** A saved filter cookie or URL naming a removed area is ignored, as an unknown area already is.

## Capabilities

### New Capabilities
- `new-england-scope`: which venues' events and which areas visitors can see on the public site.

### Modified Capabilities
- `event-geo-filter`: the offered Region, State and Metro Area options are limited to New England areas (delta in this change).
- `area-calendar-feeds`: the feed with no parameters holds New England events only (delta in this change).

## Impact

- **Code:** one list of New England state codes, used by the area options in `core/geo_filters.py` and a shared event filter applied in `core/views/index.py`, `search.py`, `calendar_feed.py`, `saved_shows.py`, `act_page.py`, `discover.py`, `core/views/act_index.py` (the A–Z next-show dates), `core/search_kinds.py` (including act next-show dates) and `core/sitemap.py`. The area options gain a New England-only mode used by the site, so `core/admin.py`'s filters, which keep the full list, are unchanged. `core/spotify_links.py` and the artist-matching commands that read it are deliberately not filtered.
- **Data:** none; no migration. The admin keeps every area in its Region, State and Metro filters; its lists open on New England, with "All areas" a click away.
- **Fetching:** `select_targets` in `core/management/commands/fetch_events.py` drops venues outside New England unless named by `--sheet-ids`. The weekly source check and venue matching still visit every venue (see the design's open questions).
- **Calendar feeds:** an old subscription such as `/calendar.ics?state=new-york` now returns the whole New England feed, because the removed area is ignored as unknown. `area-calendar-feeds` needs no spec change.
- **Not covered (phase 2 or open):** venue pages, venue search results and the location form's town and ZIP lookups still include out-of-region venues; see the design's open questions.
