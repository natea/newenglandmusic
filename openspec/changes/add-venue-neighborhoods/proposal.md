## Why

In cities, a town name says little about where a show is: "Boston" covers Allston and the Seaport, and "New York" covers all of Brooklyn. Visitors think in neighborhoods (Ball Square, Old Port, Fells Point), and the town filter added in `add-location-distance` stops at the town. A smoke test on 2026-10-28 showed that OpenStreetMap can name the neighborhood for most of our city venues, for free, with data we may store.

## What Changes

- **Each venue's neighborhood, from OpenStreetMap.** A new `lookup_venue_neighborhoods` command:
  1. finds the venue in OpenStreetMap through Nominatim's search, by its name, town and state;
  2. accepts the result only when its name matches the venue's and it's in the venue's town;
  3. reads the neighborhood from that result's address.
  
  It never sends Google Places coordinates anywhere: it uses OpenStreetMap's own location for the venue. That keeps Google's data out of it, and settles the question raised in the smoke test.
- **The best name when several are given.**
  - **The order:** prefer the familiar division ("suburb" or "quarter", such as South End or West End), then "neighbourhood".
  - **Dropped:** names that are a historic district, the town itself, a borough or a county, such as "Brooklyn" or "Kings County".
- **A fallback for New York and DC.** Where OpenStreetMap marks neighborhoods only as points, as in New York and DC, the command asks the Overpass API for the nearest neighborhood point within 1.5 km of the venue, such as Williamsburg or Shaw.
- **Neighborhoods on events.** An event at a venue with a neighborhood shows it after the town, such as "@ Big Night Live, Boston (West End)".
- **A neighborhood filter.** Once a town is chosen in the town filter, visitors can narrow it to some of its neighborhoods, as removable chips like the towns. It uses a new `neighborhood` URL parameter.
- **Editors can correct it.** In the venue admin, an editor can set a venue's neighborhood, or mark it as having none, and later runs keep the editor's choice.
- **When it runs.** The weekly job looks up venues that have never been looked up, or were looked up more than a year ago. That's about 730 lookups once, at Nominatim's limit of one request a second, then only new venues.
- **Credit.** Pages that show neighborhoods credit "© OpenStreetMap contributors", as the data's license (ODbL) asks. The credit goes in the footer and on `/privacy`'s data sources.

## Capabilities

### New Capabilities
- `venue-neighborhoods`: covers:
  - finding a venue on OpenStreetMap and choosing its neighborhood;
  - the Overpass fallback;
  - editor overrides;
  - showing neighborhoods on events;
  - the credit.

### Modified Capabilities
- `event-geo-filter`: adds a neighborhood filter within the chosen towns.
- `scheduled-jobs`: the weekly job gains `lookup_venue_neighborhoods`.

## Impact

- **Code:**
  - `core/neighborhoods.py`, with the Nominatim and Overpass clients and the name rules;
  - the `lookup_venue_neighborhoods` command;
  - `neighborhood`, `neighborhood_source` and `neighborhood_checked_at` on `Venue`, with a migration;
  - the venue admin fields;
  - `core/templates/core/event.html` for the label, which re-renders events through `Venue.save()`, since the label is in the stored HTML;
  - in `core/geo_filters.py` and the filter form, the `neighborhood` parameter and its chips;
  - one line in `bin/weekly.sh`;
  - the footer credit.
- **Services:** Nominatim (`nominatim.openstreetmap.org`) and Overpass (`overpass-api.de`, with a mirror). Both are free and need no key. Requests send the contact user agent (`API_CONTACT_EMAIL`), one Nominatim request a second, with retries and back-off for Overpass's frequent timeouts.
- **Data:** a neighborhood name per venue, storable under ODbL with credit. Nothing from Google is sent or combined.
- **Depends on** `add-location-distance`, for the town filter and its chips.
