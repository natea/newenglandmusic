## 1. One map script, two scopes

- [x] 1.1 Generalise `core/templates/map/map.html`. A toggle with `data-map="all"` maps every event on the page into `#map-all` and `#map-all-info`, and one with `data-date` maps that day, as now. For the `all` scope, pin labels give each show's date ("Nov 6", from `data-date`) before its time, in date order. Keep the day maps' code path as it is. Verify with 3.2.

## 2. The Saved shows page

- [x] 2.1 In `core/views/saved_shows.py`, pass `has_mappable`: whether any listed event has a located venue, no venue override, and isn't cancelled. In `core/templates/core/saved.html`, when `has_mappable` and `protomaps_api_key`, include `map/map.html` in the head and add a "SHOW MAP" toggle (`data-map="all"`), `#map-all` and `#map-all-info` above the list, styled like the day maps. Verify with 3.1.

## 3. Tests

- [x] 3.1 Add render tests to `core/tests/test_saved_shows.py`. Verify that they pass. They cover:
  - the toggle and containers shown with mappable saved shows and a key;
  - no toggle without a key;
  - no toggle with nothing mappable: only venue overrides, unlocated venues, or cancelled shows;
  - the listing's day-map links unchanged.
- [x] 3.2 Add `core/tests/test_saved_shows_map_browser.py`, on `BrowserTestCase`, with a dummy `PROTOMAPS_API_KEY`. Verify that it passes offline. It covers:
  - not loaded until opened;
  - a map over several days: pins and labels with "Nov 6"-style dates, read from the map's source;
  - shows at one venue sharing a pin;
  - clicking a pin listing its shows, with their icon rows, in `#map-all-info`;
  - shows that can't be mapped getting no pin but staying listed;
  - "HIDE MAP";
  - the day maps unchanged, as a day map's pins and time-only labels.

## 4. Check

- [x] 4.1 Run the whole suite with outbound network blocked. Then, on the local site, save shows in two towns, open `/saved`'s map, and check the pins, labels and clicking. Verify that the tests pass and the map works by hand.
