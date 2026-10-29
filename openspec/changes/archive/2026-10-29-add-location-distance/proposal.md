## Why

Visitors want to know which shows are near them, but the listing only says which town each venue is in. They have to know the area to judge how far that is. A region, state or metro filter narrows the list, but within a metro area like Boston's, the towns can be an hour apart. Visitors can't pick the towns they'll actually travel to.

## What Changes

- **"How far" labels on events.** A visitor can give a location:
  - typing a ZIP code ("02144") or a town ("Somerville" or "Somerville, MA");
  - or pressing "Use my location", which asks the phone or browser for its position.
  
  Then each event at a located venue shows how far away it is, such as "(0.5 mi away)", on the listing, the month archives, the saved shows page and the map panels. The events stay in time order. The location is remembered in a cookie, and can be cleared.
- **ZIP and town lookup from Census data.** A new `load_census_gazetteer` command loads the Census Bureau's Gazetteer files into a lookup table, with no API, key or per-search request. The files are the ZIP Code Tabulation Areas, the county subdivisions (New England's towns), and places (cities, villages and boroughs). They're public domain, and the year is configurable; 2026 is the current one. A name that several towns share, such as Springfield, offers a choice.
- **Towns within a metro area.** Once a metro area is chosen, the filter offers a multi-select of the towns in it that have venues. The chosen towns narrow the listing, with a new `town` URL parameter that can be repeated. They're remembered with the rest of the filter, and work without JavaScript.
- **Ready for the venue list.** The location lookup and distance calculation live in one module (`core/location.py`), so the planned master venue list can sort by distance to the same location. The venue list itself isn't part of this change.

## Capabilities

### New Capabilities
- `event-distance`: covers:
  - setting, remembering and clearing a visitor's location from a ZIP, a town or the device's position;
  - the Census lookup table and its loader;
  - the distance labels on events.

### Modified Capabilities
- `event-geo-filter`: adds a multi-select of a metro area's towns, the `town` parameter, and its place in the remembered filter.

## Impact

- **Code:**
  - `core/location.py`, for lookup, distance and formatting;
  - a `CensusPlace` model and its migration;
  - the `load_census_gazetteer` command;
  - a `/location` view (GET and POST) for setting and clearing the location;
  - the distance label added in `core/templatetags/event_actions.py` (`event_html`), next to the icon row;
  - a location form in the listing templates;
  - a small `core/static/core/js/location.js` for "Use my location";
  - in `core/geo_filters.py`, the `town` parameter and the metro's town list;
  - in `core/templates/core/geo_filter_form.html`, the town multi-select.
- **Data:** about 33,800 ZIP areas, 36,400 county subdivisions and 32,000 places, a few MB in Postgres. They're loaded once a year with `load_census_gazetteer`, not by the daily job.
- **Privacy:** the location cookie holds coordinates rounded to about 100 m, and the label the visitor gave. The server uses it only to work out distances, and keeps nothing. `/privacy` gets a line about it, and about the Census data.
- **No new dependency or key.** Distances use the haversine formula, and the Census files are plain text read by the standard library.
- **Open question, the same as the maps':** the distances use `Venue.exact_location`, the Google Places position when the match is confident. That's the same data as the day maps' pins, so whatever settles the Google map question settles this too. The fallback is the sheet's town-centre coordinates, which are good enough for "how far".
