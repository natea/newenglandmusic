## Context

- `map/map.html` handles day maps (`a[data-date]`) and a page-wide map (`a[data-map="all"]`, used by `/saved`): it collects `div.event[data-venue-lnglat]` across the page, merges venues within about 50 m, labels pins with each show's date and time, and exposes `window.siteMaps[key]` for tests.
- `/?s=…` renders `core/templates/core/search.html` from `core/views/search.py`: every matching event, past and upcoming, newest first, each through the `event_html` tag (so the icon row, save state and distances are per visitor). The search page doesn't include `map/map.html` today.

## Goals / Non-Goals

**Goals:** a map of the upcoming results, reusing the Saved shows map's behaviour.

**Non-Goals:** reordering or splitting the results list; mapping past shows; a map of matched static pages.

## Decisions

**1. Mark the upcoming results, and let the "all" scope be limited to them.** The view passes the start of today (New York time); the template wraps each upcoming result in `<div class="upcoming-result">`. The toggle carries `data-map="all" data-map-events=".upcoming-result"`, and `map.html` selects `${eventsSelector} div.event[data-venue-lnglat]` when `data-map-events` is set, else the whole page as now. The same selector applies when a pin's shows are listed below the map, so past shows at the same venue aren't listed either. Alternative rejected: comparing `data-date` in the browser, which would need the New York date in JavaScript and duplicate the server's idea of "upcoming".

**2. `has_mappable` like `/saved`.** The view checks the upcoming results for one that isn't cancelled, has no venue override, and has a venue with `exact_latitude`/`exact_longitude` — the same test `core/views/saved_shows.py` uses, moved into a shared helper so the two can't drift.

**3. Same look.** The toggle, the map box and the info panel copy `/saved`'s markup and styles.

**How it's tested.** Nothing reaches the network.
- **Render tests:** the toggle and containers with upcoming located results and a key; none with only past results, no key, or only unmappable results; past results still listed; the upcoming wrapper only around upcoming results.
- **Playwright browser tests** on `core/tests/browser.py` (which aborts every outside request, including Protomaps' tiles): no map before the click; one pin for The Beehive's two upcoming shows with their date labels, past ones unpinned; two venues fitted; clicking a pin lists only upcoming shows; "HIDE MAP"; a day map and the Saved shows map unchanged. Search uses Postgres full-text search, which the test database supports.

## Risks / Trade-offs

- **[Search matches many upcoming shows]** → A broad search ("jazz") could pin hundreds of shows; pins merge by venue, so it's one pin per venue, as on the Saved shows map.
- **[The Places/Google Map question]** → Same data and map as the other maps; settled together.

## Migration Plan

Deploy. No data change, no re-render.
