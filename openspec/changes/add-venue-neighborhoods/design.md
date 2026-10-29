## Context

- **The smoke test (2026-10-28):** Nominatim's reverse lookup on 12 venues' positions named the right neighborhood for most:
  - West End, East Cambridge, Ball Square, South Philadelphia, Old Port, South End and Downtown Baltimore;
  - historic districts for Providence, New Haven and Northampton;
  - only "Brooklyn" for a Brooklyn venue, and nothing for the 9:30 Club in DC.
  
  Overpass, which can find point-only neighborhoods, timed out on both public servers that day.
- **The coordinates question:** the positions in the smoke test came from Google Places. Google's terms limit using Places content with other services, so this design finds each venue on OpenStreetMap by name instead.
- **What exists:**
  - venues have `name`, `city_town` and `state` from the sheet;
  - the town filter (`add-location-distance`) lists a metro's towns, as removable chips;
  - events' venue line is in their stored HTML (`core/templates/core/event.html`);
  - `core/user_agent.py` gives the contact user agent.

## Goals / Non-Goals

**Goals:**
- A neighborhood for city venues, from storable open data, without sending Google data anywhere.
- Shown on events, and filterable within a town.

**Non-Goals:**
- Neighborhood boundaries, or "near this neighborhood" searches.
- Neighborhoods for visitors' own locations.
- Replacing Google Places coordinates for map pins. That could reuse this lookup later, as OpenStreetMap's own location for each venue, but it's a separate decision.

## Decisions

**1. A forward search by name, not a reverse lookup on Google's coordinates.**
- **How:** `GET /search?q=<name>, <town>, <state>&countrycodes=us&format=jsonv2&addressdetails=1&limit=5`. One request gives the venue's OpenStreetMap location and its address, including the suburb or neighbourhood.
- **Which result:** the first whose normalized name equals the venue's, or contains it as whole words, and whose address's city, town or village equals the venue's town, with the right state.
- **Alternative rejected:** reverse-geocoding Google Places coordinates. It's the more reliable lookup, but it sends Google content to another service, which may break Google's terms. Revisit if the Google question is settled the other way.
- **Coverage:** a venue OpenStreetMap doesn't know by name gets no neighborhood. Coverage is measured by the first run (see Open Questions).

**2. Choosing the name.**
- **The order:** `suburb`, `quarter`, `neighbourhood`, `city_district`.
- **Skipped:** names ending in "Historic District"; names equal to the town; names of New York's five boroughs; names ending in " County".
- **Why this order:** suburb and quarter are the names people use (South End, West End, South Philadelphia). Neighbourhood is often a micro-area or a historic district.
- **Alternative rejected:** the most specific name first, which gave "Five Sisters" over "South End" in Burlington.

**3. The Overpass fallback.**
- **The query:** `node(around:1500,<lat>,<lon>)["place"~"^(neighbourhood|suburb|quarter)$"];out;`, sent by POST.
- **The answer:** the nearest node by haversine distance, if its name is usable.
- **When:** only when the address gives no usable name and the venue is in New York (any borough) or Washington, DC (`POINT_NEIGHBORHOOD_TOWNS`). The first dry run (2026-10-29) asked Overpass for small-town venues too, such as one in Danbury, CT, and its busy servers cost over two minutes each. Elsewhere, an address without a neighborhood means there's none worth naming.
- **Busy servers:** retry after 5, 15 and 45 s, then the mirror `overpass.private.coffee`, then leave the venue due.

**4. Storage.**
- **The fields:** `Venue.neighborhood` (blank allowed), `neighborhood_source` ("" | "address" | "overpass" | "editor" | "none"), `neighborhood_checked_at`.
- **License:** ODbL allows storing it, with credit.
- **Saving:** with `queryset.update()`. Only venues whose neighborhood changed are re-rendered (`rebake` of their upcoming events), so a full run doesn't re-render everything.

**5. Showing it.** `event.html` appends " (<neighborhood>)" after the venue's town. The value is in the stored HTML, so a change re-renders the venue's upcoming events.

**6. The neighborhood filter.**
- **The parameter:** `GeoFilter` gains `neighborhoods`, a list of (neighborhood, town, state), parsed from `neighborhood` values and kept only when they're within the chosen towns.
- **The query:** `q()` ANDs an OR of `Q(venue__neighborhood__iexact=…, venue__city_town__iexact=…, venue__state=…)`.
- **The chips:** `town_chips.js` is generalized to any `select[multiple]` in the filter form, so neighborhoods get the same chips.

**7. Scheduling.** The weekly job's last step, with the default `--limit 300`. The first runs take about 730 lookups, over three weeks or one manual run; after that, only new venues and yearly refreshes.

**How it's tested.** Nothing reaches the network, and the suite passes with outbound requests blocked.
- **Nominatim and Overpass:** `core.neighborhoods` takes an injectable session, sleep and clock. A fake session answers searches and Overpass queries from hand-written JSON in their documented shapes (`core/tests/fixtures/osm/`), built from the smoke test's real answers: Big Night Live, Century, Cafe Nine, 18th Ward Brewing and a Williamsburg node. It also returns 429s and timeouts.
- **The Google check:** the tests assert that no request contains a venue's `place_id` or Places coordinates.
- **The listing and filter:** render tests and Playwright tests on the existing browser base.

## Risks / Trade-offs

- **[OpenStreetMap doesn't know a small venue by name]** → No neighborhood for it, which matters little in small towns. Editors can fill in the important ones in the admin.
- **[A wrong match by name]** → Requiring the venue's town and state, and a whole-word name match, limits this. Editors can clear it.
- **[Overpass outages]** → Venues are left due for the next week, and nothing breaks.
- **[Nominatim's usage policy]** → One request a second, a real contact, no bulk scraping. About 730 requests once, then a handful a week, is well within it.

## Migration Plan

1. Deploy the migration, the code and the footer credit.
2. Run `lookup_venue_neighborhoods --dry-run --limit 30` locally, and check the names by hand.
3. Run it for real locally, and once on Render, with the user's approval.
4. The weekly job takes over.

**Rollback:** blank the neighborhoods (one admin action), which re-renders the venues' events.

**First dry run (2026-10-29, Connecticut's small cities first):** of 9 venues, 1 got a neighborhood (BRYAC, "Black Rock" in Bridgeport), 1 was found with no neighborhood, and 6 aren't on OpenStreetMap at all (Park City Music Hall, RoadRunner Kitchen + Bar, Bleacher's Bar…). Small-town venues are often missing from OpenStreetMap, which matters little: neighborhoods are mostly a city thing.

**Second dry run (2026-10-29, Massachusetts, 30 venues from Allston to Boston):** 15 got a neighborhood from their address, all right where checked (Paradise Rock Club: Packard's Corner; House of Blues, MGM Music Hall and The Bebop: Fenway-Kenmore; Orpheum Theatre: Downtown; Capitol Theatre: East Arlington), 2 were found with none, and 13 aren't on OpenStreetMap by name, including well-known rooms (Big Night Live, Royale, Rockwood Music Hall, The Beehive) and every Porchfest. Editors can fill in the important ones; a later change could look up the misses by OpenStreetMap or Census coordinates.

## Open Questions

- **What share of venues OpenStreetMap knows by name.** The first dry run will tell. If it's low for city venues, a later change could add a reverse lookup on OpenStreetMap or Census coordinates for the venues it misses.
