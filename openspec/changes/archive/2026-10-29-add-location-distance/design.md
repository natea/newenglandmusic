## Context

- **The geo filter:**
  - `core/geo_filters.py` parses `region`, `state` and `metro` into a `GeoFilter`, and remembers it in a cookie, redirecting `/` to the remembered filter. The listing pages and `/calendar.ics` use it.
  - Areas are `GeoArea` rows, synced from the sheet's `geo-filters_json` tab. A metro lists its states plus counties or cities.
- **Per-visitor parts of a page:** each event's HTML is stored baked. Per-visitor parts, the icon row and the save state, are added when a page is rendered, by the `event_html` template tag (`core/event_actions.py`), at a placeholder.
- **Event coordinates:** events carry their venue's coordinates (`Venue.exact_location`: the Google Places position when confident, else the sheet's town centre). The day maps use them.
- **The Census Gazetteer files (checked 2026-10-28),** at `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/<year>_Gazetteer/<year>_Gaz_{zcta,cousubs,place}_national.zip`:
  - "|"-separated text, in the public domain;
  - 2026 has 33,791 ZCTAs (`GEOID`, `INTPTLAT`, `INTPTLONG`), 36,427 county subdivisions (`USPS`, `NAME` such as "Somerville city", and the coordinates) and about 32,000 places;
  - each zip file is about 1 to 1.5 MB.
- **The regions may move into Django:** the user may later replace the sheet's geo filters with regions managed in Django.

## Goals / Non-Goals

**Goals:**
- A distance label on every event at a located venue, for a location given as a ZIP, a town, or the device's position.
- Narrowing a metro area to some of its towns.
- A location module the future venue list can reuse.

**Non-Goals:**
- Re-ordering events by distance, or a radius filter. Events stay in time order, as the user asked.
- The master venue list itself.
- Driving or transit distances, which would need a routing API. Straight-line distance is enough to judge "near".
- Neighborhoods, from OpenStreetMap: a later change.
- Moving the regions from the sheet into Django. The town filter doesn't depend on where the regions are defined.

## Decisions

**1. The Census Gazetteer files over GeoNames or a package.**
- **Why:** public domain, so no credit is required. New England's real towns, as county subdivisions. Small plain-text files.
- **Alternatives rejected:**
  - **pgeocode:** needs pandas, and downloads at runtime;
  - **django-cities-xtd:** needs GeoDjango, PostGIS and GDAL, and probably a move to Docker on Render;
  - **django-cities-light:** has no ZIP codes;
  - **GeoNames:** needs a credit link, and uses postal place names rather than towns;
  - **the Census geocoder API:** a request for every search, and an occasionally unavailable server.
- **The model:** `CensusPlace(kind: zip|town, name, state, search_key, latitude, longitude)`, with an index on `(kind, search_key)`. `search_key` is the name normalized like artist names, without accents or punctuation, in lowercase.
- **Loading:** the command downloads to a temporary directory, parses, and replaces the table in one transaction. A failed download leaves the old table.
- **Suffixes:** dropped by a fixed list ("city", "town", "CDP", "village", "borough", "township", "plantation", "gore", "grant", "location", "purchase", "municipality"), so "Somerville city" becomes "Somerville". A name that's all suffix, such as "Town", is kept as it is.

**2. Location is resolved on the server, and kept in a cookie.**
- **The form:** a GET form posts to `/location`. The `q` field holds the typed place. `lat` and `lon` come from "Use my location", whose script calls `navigator.geolocation.getCurrentPosition` only on the button press, rounds to three decimals, and submits.
- **The view:**
  - resolves the place through `core.location.resolve(text)`;
  - on success, sets the cookie `near`, holding `label|lat|lon`, URL-encoded, for one year;
  - redirects to `next`, which must be a local path;
  - on several matches, renders a small choice page linking to `/location?q=Springfield, MA&next=…`;
  - on no match, redirects with a `location_error` message (Django messages).
  
  `/location?clear=1` deletes the cookie.
- **Why a cookie and not a URL parameter:** a location is personal, and shouldn't end up in links people share. The geo filter goes in the URL because it's about what's listed. The location only changes the labels.
- **No JavaScript:** typing a ZIP or town works without JavaScript. Only "Use my location" needs it, and it's hidden without JavaScript.

**3. Distances are added at render time, next to the icon row.**
- **How:** `event_html` gains the visitor's location from the request cookie, parsed once per request and cached on the request. `actions_html` appends `<span class="event-distance">(0.5 mi away)</span>` to the row when the location is set and the event's venue has coordinates.
- **The coordinates:** the venue's coordinates are already loaded with the event (`select_related("venue")`) and come from `exact_location`, so no extra query is needed.
- **The maths:** `core.location.miles(a, b)` is the haversine distance in statute miles, with an Earth radius of 3,958.8 mi. `format_miles` follows the spec's rounding.
- **Speed:** about a thousand rows a page means a thousand haversine calls, well under a millisecond each.

**4. Towns in a metro come from the venues, not the sheet.**
- **The town list:** `metro_towns(metro)` returns the distinct `(city_town, state)` of venues matching `area_q(metro)`, sorted.
- **The filter:** `GeoFilter` gains `towns`, a list of `(town, state)` pairs. `parse_geo_filter` reads repeated `town` values as "Town, ST", and keeps only those in `metro_towns(metro)`. `q()` adds `Q(venue__city_town__iexact=…, venue__state=…)` OR'd across the towns. `query_string` includes them, so the cookie, the month links and the feeds carry them.
- **The form:** a `<select multiple name="town">` shown when a metro is chosen. The page's existing auto-submit script submits on change.
- **Why venue towns:** they're what the listing can actually narrow to, and they don't depend on the sheet's metro city lists. If regions move into Django, `GeoArea` becomes admin-managed, and this keeps working unchanged. The Census town table could then help define metros by real towns.

**5. One module for the venue list to reuse.** `core/location.py` holds `resolve()`, `location_from_request()`, `miles()` and `format_miles()`. A future venue list sorts with `sorted(venues, key=lambda v: miles(location, v.exact_location))`.

**How it's tested.** Nothing reaches the network, and the suite passes with outbound requests blocked.
- **The Census files:** `load_census_gazetteer` takes an injectable session, and the tests serve small zip files built in the test from a few lines in the real format. That covers Somerville city MA and Somerville town ME, Hamden town CT and NY, three Springfields, and ZIPs 02144 and 05656. A failing response tests the unchanged table.
- **The browser's position:** the Playwright browser tests use `context.grant_permissions(["geolocation"])` and `context.set_geolocation(...)`, and a denied-permission context for the refusal. There's no real geolocation service, and the browser base aborts any outside request.
- **Everything else:** the location view, the labels, the town filter and the feeds are covered by render tests with `CensusPlace` rows created in the test.

## Risks / Trade-offs

- **[Distances from Google Places coordinates]** → This is the same open question as the day maps. If it's settled against using them, `exact_location` falls back to the sheet's town centres, which still give a useful "how far". Recorded in PRODUCTION.md's launch checklist item.
- **[ZCTAs aren't exactly ZIP codes]** → PO-box-only ZIPs aren't in them. Those get "not found", with a suggestion to type the town.
- **[Town names that venues spell differently]** → Venues' `city_town` comes from the sheet, so its spelling is the sheet's. The town multi-select lists those spellings, so it always matches. Typed-town lookup uses Census names, which only need to be close to the venue, not match it.
- **[Privacy]** → The cookie holds a coordinate to about 100 m. It's only read to compute labels, and never logged or stored. `/privacy` says so.

## Migration Plan

1. Deploy the model and migration.
2. Run `load_census_gazetteer --year 2026` locally, and once on Render with the user's approval.
3. The location form appears once the table has rows. An empty table hides the form, so the deploy order doesn't matter.

**Rollback:** remove the form from the templates. Visitors' cookies are then simply ignored.
