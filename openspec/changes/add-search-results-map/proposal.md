## Why

A search like `/?s=beehive` lists every matching show, past and upcoming, but gives no way to see where they are. The listing's day maps and the Saved shows map already put a page's shows on a map; search results are the one event list without one.

## What Changes

- **A "SHOW MAP" toggle on the search results page,** above the results, like the Saved shows page's. Opening it shows one map with a pin for every **upcoming** result at a located venue, labelled with each show's date and time ("Nov 6 7:00pm …"), fitted to the pins. Clicking a pin lists its shows below the map, with their icons and play buttons.
- **Past results stay listed but aren't pinned.** Search lists past shows too, newest first, and pinning years of past shows would bury the ones you can still go to. The list's order is unchanged.
- **The same map script.** `map/map.html`'s page-wide "all" scope, built for the Saved shows map, learns to limit itself to part of the page (`data-map-events`), so search pins only the upcoming results. Day maps and the Saved shows map behave as before.
- **Like the other maps:** shown only when a Protomaps key is set and at least one upcoming result can be pinned; nothing loads until the toggle is clicked.

## Capabilities

### New Capabilities
- `search-results-map`: the map of upcoming search results.

### Modified Capabilities
None. The Saved shows map's requirement is unchanged; the script change is internal.

## Impact

- **Code:** `core/views/search.py` (which results are upcoming, and `has_mappable`), `core/templates/core/search.html` (the toggle, the map containers, and a wrapper marking upcoming results), `core/templates/map/map.html` (the optional `data-map-events` selector).
- **No model, migration, dependency or re-render.**
- **Same open question as the other maps:** the pins use the venues' Google Places coordinates on a Protomaps map (see PRODUCTION.md's launch checklist).
