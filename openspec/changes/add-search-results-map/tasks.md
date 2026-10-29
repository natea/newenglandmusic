## 1. Map script and view

- [ ] 1.1 Let `map/map.html`'s "all" scope take an optional `data-map-events` selector, used both for the pins and for the shows listed under a clicked pin. Verify with the existing Saved shows map and day map browser tests still passing.
- [ ] 1.2 In `core/views/search.py`, pass the start of today (New York time) and `has_mappable` for the upcoming results, with the mappable test moved into a helper shared with `core/views/saved_shows.py`. Verify with render tests for the toggle shown, and not shown with only past results, no key, or only unmappable results.

## 2. Template

- [ ] 2.1 In `core/templates/core/search.html`, include `map/map.html` when `has_mappable` and a key are set, add the "SHOW MAP" toggle (`data-map="all" data-map-events=".upcoming-result"`), `#map-all` and `#map-all-info` above the results, and wrap upcoming results in `.upcoming-result`. Verify with render tests that past results are still listed, and only upcoming ones are wrapped.

## 3. Browser tests and check

- [ ] 3.1 Add Playwright tests for: not loaded until opened; map of upcoming results (The Beehive, past shows unpinned); results at several venues; clicking a pin; "HIDE MAP"; other maps unchanged. Verify that they pass offline.
- [ ] 3.2 Run the whole suite with outbound network blocked, then try `/?s=beehive` on the dev server. Verify that the tests pass and the map works by hand.
