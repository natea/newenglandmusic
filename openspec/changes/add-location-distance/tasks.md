## 1. Census lookup data

- [x] 1.1 Add `CensusPlace` (kind, name, state, search_key, latitude, longitude, with an index on kind and search_key), and its migration. Verify that `makemigrations --check` is clean and that the migration applies.
- [x] 1.2 Add the `load_census_gazetteer [--year]` command, with an injectable session. It:
  - downloads the ZCTA, county subdivision and place files;
  - strips the Census suffixes;
  - de-duplicates by name and state;
  - replaces the table in one transaction;
  - leaves it unchanged when a download fails.
  
  Verify with tests serving small zip files built in the test, covering "Loading the data" and "Download fails".

## 2. Location module and view

- [x] 2.1 Add `core/location.py`:
  - `resolve(text)`, which returns a location, a list of choices, or None;
  - the cookie's encoding and decoding, with coordinates rounded to three places;
  - `location_from_request()`;
  - `miles()`;
  - `format_miles()`.
  
  Verify with unit tests for each of the spec's lookup scenarios: ZIP code, town and state, town name only, several towns with the name, and not found. Also the haversine distance against a known pair, and the label rounding (under 0.1, under 10, 10 and over).
- [x] 2.2 Add `/location` (GET and POST), for typed places, device coordinates, choices and clearing. It redirects only to a local `next`, and shows messages for not found and refused positions. Verify with view tests for:
  - a typed location;
  - several matches offered;
  - not found;
  - clearing;
  - an outside `next` refused;
  - nothing stored on the server.

## 3. Distance labels

- [x] 3.1 In `event_html` and `actions_html`, append `(… mi away)` for events at located venues when a location is set. Add its style. Verify with render tests for distances shown, far away, no coordinates (an override, and an unlocated venue) and no location. Also check that the stored HTML is unchanged, and that the saved shows page shows labels too.
- [x] 3.2 Add the location form to the listing, month archive and saved shows templates, showing the current label and a "clear" link, hidden while the Census table is empty. Add `core/static/core/js/location.js` for "Use my location". Verify with Playwright tests:
  - device location set, with granted geolocation at a set position;
  - position refused, with permission denied;
  - the label shown on the listing after setting a typed location.

## 4. Towns in a metro

- [x] 4.1 Add `metro_towns()` and the `town` parameter to `core/geo_filters.py`: parsing, validation against the metro, `q()`, `query_string` and the cookie. Verify with tests for:
  - two towns in a metro;
  - town outside the metro;
  - town without a metro;
  - remembered;
  - the calendar feed.
- [x] 4.2 Add the town multi-select to `core/templates/core/geo_filter_form.html`, shown when a metro is chosen. Verify with render tests for the towns offered and the selected towns. Also check that it submits without JavaScript, and that changing the metro drops other metros' towns.

## 5. Docs and check

- [x] 5.1 Add the Census data and the location cookie to `/privacy`. Add `load_census_gazetteer` to PRODUCTION.md and AGENTS.md: how often to run it (once a year, and at setup) and the data's source. Add the Google-coordinates note to the launch checklist item. Verify with the privacy page test and by reading the docs.
- [x] 5.2 Run the whole suite with outbound network blocked. Then run `load_census_gazetteer --year 2026` locally, set a location by ZIP, by town and by "Use my location" on the dev server, and narrow the Boston Metro Region to Somerville and Cambridge. Verify that the tests pass and that the labels and the filter work by hand.
