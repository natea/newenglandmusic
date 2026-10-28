## Why

A visitor's saved shows are often spread over several towns. The listing's day maps show where one day's shows are, but the Saved shows page has no map. That leaves no way to see all the saved shows on one map, for example to spot which are close together.

## What Changes

- **A map of the saved shows on `/saved`:**
  - a "SHOW MAP" toggle above the list, like each day's on the listing, opens one map with a pin for every upcoming saved show at a located venue;
  - the map fits itself to the pins;
  - shows at the same venue, or within about 10 metres, share a pin;
  - each pin's label gives the date and time of each show, for example "Nov 6 7:00pm";
  - clicking a pin lists those shows under the map, as the day maps do, with their icons and play buttons.
- **One map script for both:** the day maps' script (`map/map.html`) learns a second kind of map, covering every event on the page instead of one day's, so both maps behave and look the same. The day maps don't change.
- **Shows without a location** (no venue, or a venue with no coordinates) and cancelled shows stay in the list but get no pin. Otherwise a show is pinned exactly as the day maps pin it. When no saved show can be mapped, the toggle doesn't appear.
- **Like the day maps:** the map only appears when a Protomaps key is set, and nothing loads until the visitor opens it.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `saved-shows`: adds a requirement, a map of the saved shows on the Saved shows page.

## Impact

- **Code:**
  - `core/templates/map/map.html`, which handles a page-wide map as well as day maps;
  - `core/templates/core/saved.html`, which gets the toggle, the map and its info panel;
  - a map label that includes the date. Events already carry `data-date`; the pins can show it formatted.
- **No model, migration or dependency.** No re-render either: the toggle and the map are in the page template, and events already carry their coordinates in their stored HTML.
- **Tests:**
  - render tests: the toggle shown only with mappable saved shows and a key;
  - Playwright browser tests: opening the map, pins and labels, and clicking a pin. These stay offline: the tests abort the map style and tile requests, and check the map's data and the info panel, not the drawn tiles.
- **Open question carried over:** the day maps show Places-derived coordinates on Protomaps. Google's terms want Places results shown on a Google Map, and the site stays unshared until that's settled (see `PRODUCTION.md`'s launch checklist). This map uses the same coordinates and the same map setup, so whatever settles the day maps settles this one too.
