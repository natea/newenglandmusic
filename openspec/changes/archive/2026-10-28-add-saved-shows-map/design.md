## Context

- **How the day maps work.** `core/templates/map/map.html`, included in the page head when `protomaps_api_key` is set, attaches to every `a[data-date]` "SHOW MAP" link on the listing. Clicking one:
  - reads that day's events, `div.event[data-date=…][data-venue-lnglat]`;
  - merges venues within about 10 metres into one pin;
  - builds GeoJSON with the time and the start of the title;
  - creates a MapLibre map in `#map-<date>`, using a Protomaps style, fitted to the pins;
  - on a pin click, copies that pin's events into `#map-<date>-info`.
- **What events carry:** `data-date` (mmddyy), `data-starttime`, `data-venue-lnglat`, `data-venue-id`, `data-title-and-artists` and `data-is-cancelled`, all in their stored HTML.
- **The Saved shows page** (`core/templates/core/saved.html`, `core/views/saved_shows.py`) lists the visitor's upcoming saved shows by date. It doesn't include `map.html` yet.

## Goals / Non-Goals

**Goals:**
- One map of all the saved shows, behaving and looking like the day maps.
- One script for both kinds of map, so they don't drift apart.

**Non-Goals:**
- Grouping the Saved shows list by venue or location. That's a later `group=` value.
- Directions, routes or clustering beyond the existing 10-metre merge.
- Settling the Google-Map question for Places coordinates (see the proposal).

## Decisions

**1. Generalise `map.html` with a map scope, rather than writing a second script.**
- **How it works:**
  - a toggle link carries `data-date="<mmddyy>"`, a day map as now, or `data-map="all"`, a map of every event on the page;
  - the script picks its events with `[data-date="…"]` or with no date filter, and its container with `#map-<date>` or `#map-all`, the info panel following the same names;
  - pin labels include the date when the scope is `all`.
- **What stays shared:** the venue merging, GeoJSON, markers, hover, click and info-panel code, which already work per container.
- **Alternative rejected:** a separate script for `/saved`. It would duplicate about 250 lines, which would drift.

**2. Labels with the date.**
- **How it works:** for the `all` scope, each event's label is its date, formatted from `data-date` in the browser ("Nov 6"), then its start time. A pin with several shows lists them in date order, each "Nov 6 7:00pm", one per line, with the start of each title, as the day maps already join theirs.
- **Why the browser:** formatting there keeps the stored HTML unchanged, so no re-render is needed.

**3. The toggle only when there's something to map.**
- **How it works:** the view checks, among the listed events, for any not cancelled with a venue having `exact_latitude` and `exact_longitude`, which is what makes an event carry `data-venue-lnglat`, and passes `has_mappable`.
- **Venue overrides:** an event with a venue override is pinned at its venue, as the day maps already do, because its stored HTML carries the venue's coordinates. No event on the site has an override (checked 2026-10-28). Unpinning them would mean changing the stored HTML and re-rendering, for no current case. The template shows the toggle and containers only when that's true and `protomaps_api_key` is set, and includes `map/map.html` in the page head under the same condition.
- **Why not leave it to the script:** checking on the server keeps an empty map from ever appearing, without JavaScript deciding.

**4. Unchanged behaviour for the day maps.** Their links keep `data-date`, and the script's behaviour for that scope is the same code path, so existing day-map behaviour, and the map-related tests in `core/tests/test_event_venue_map.py`, stay as they are.

**How it's tested.** No outside service is reached.
- **Render tests** cover:
  - the toggle and containers with mappable saved shows and a key;
  - no toggle without a key, or with nothing mappable, such as only venue overrides, unlocated venues or cancelled shows;
  - the day map links unchanged on the listing.
- **Playwright browser tests** (`core/tests/browser.py` aborts every request that isn't to the test server, including Protomaps' style and tiles, and the map is created regardless) cover:
  - no map before the click;
  - after "SHOW MAP": the map's GeoJSON source, read through the page's `map` object, holding the expected pins and labels with dates, and shared pins;
  - a pin click listing its shows in `#map-all-info`, triggered through MapLibre's click handler by firing a synthetic click at the pin's projected point;
  - "HIDE MAP" hiding it.
- **Test settings:** `PROTOMAPS_API_KEY` is set to a dummy value for the browser tests.

## Risks / Trade-offs

- **[Testing a map without its tiles]** → Assert on the map's data source and the info panel rather than drawn pixels. If clicking a feature is unreliable without the style loaded, the click test calls the same handler with the pin's feature instead. That's still the page's own code, run in the browser.
- **[One script, two scopes]** → Small risk of breaking the day maps. That's covered by keeping their path unchanged and adding a browser test of a day map.
- **[The Places/Google Map question]** → Unchanged by this change: same data, same map provider as the day maps. See the proposal.

## Migration Plan

Deploy. There's no data change, and no re-render.
