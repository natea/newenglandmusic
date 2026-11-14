## Why

Massachusetts, where most of the site's venues are, has only seven broad metros ("MA: Central" runs from Acton to Athol), so the location filter can't narrow to the places people actually go out in. The editors have drawn up 28 sub-regions in seven groups, from the Berkshires to the Elizabeth Islands. And the venue sheet is being retired: the daily sync stops, venues are kept in the admin, and the areas the sync used to load from the sheet need a home in the code.

## What Changes

- **Massachusetts's seven metros are replaced by 28 sub-regions,** in seven groups (Western Massachusetts, Central Massachusetts, MetroWest, Greater Boston, Northeast Massachusetts, South of Boston & Southeast, Cape Cod & the Islands), each with the towns the editors listed, and the Boston sub-regions with their neighborhoods.
- **Every Massachusetts venue lands in exactly one sub-region:** by its town when a sub-region lists it, by its Boston neighborhood for Boston's sub-regions, and otherwise by its county's default sub-region, so no venue falls outside them.
- **The filter shows the groups as headings** in the Metro Area options, with the sub-regions under them; choosing a sub-region lists its towns, then neighborhoods, as metros do today.
- **Old Massachusetts metro addresses** (`metro=ma-boston-metro-region`, saved filters, and subscribed calendar feeds such as `/calendar.ics?metro=ma-cape-cod`) **cover all of Massachusetts** instead of being dropped, which would widen them to every area. `ma-north-shore` keeps working as the new North Shore, which has the same address.
- **All areas are defined in the code** (regions, states, every state's metros, and the new sub-regions), in one data file, loaded on deploy; editors change them through the code.
- **BREAKING (operations): the daily sheet sync stops.** `sync_venues_from_gsheets` leaves the daily job, and no longer reads or changes areas; the command stays for a manual, previewed import. Venues are edited and added in the admin, and a venue added there gets the next venue ID automatically.

## Capabilities

### New Capabilities
- `venue-records`: venues are kept in the admin once the sheet is retired, including the ID a new venue gets.

### Modified Capabilities
- `event-geo-filter`: areas come from the code's data file rather than the sheet; Massachusetts's sub-regions and their matching rules (towns, Boston neighborhoods, county defaults, one sub-region per venue); the Metro Area options grouped under the sub-regions' groups; old Massachusetts metro addresses covering Massachusetts.
- `venue-sheet-sync`: the sync no longer loads regions, states and metros from the sheet's `geo-filters_json` tab.
- `scheduled-jobs`: the daily job no longer runs `sync_venues_from_gsheets`.

## Impact

- **Code:** a new data file of areas (e.g. `core/geo_areas.py`) and the code that loads it into `GeoArea` on migrate; `GeoArea` gains a group label and a list of neighborhoods, and its matching (`core/geo_filters.py`: `area_q`, `metro_groups`, `metro_towns`, `parse_geo_filter`) learns the sub-regions' rules and old-slug fallback; `sync_venues_from_gsheets` loses its area step; `bin/daily.sh`; the venue admin (the automatic ID).
- **Migration:** one schema migration for the two `GeoArea` fields; the areas themselves are loaded from the data file on every migrate, replacing what the sheet loaded.
- **Data:** the current regions, states and non-Massachusetts metros are copied from the stored areas into the data file as they are; venue rows are untouched.
- **Docs:** `AGENTS.md` and `PRODUCTION.md` say venues no longer come from the sheet, and how to change an area.
- **No external services** and no cost; the Google service account stays only for a manual import.
