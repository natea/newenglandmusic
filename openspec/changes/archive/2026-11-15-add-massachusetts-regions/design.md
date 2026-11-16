# Design

## Context

- `GeoArea` (region, state or metro; `sheet_id`, `label`, `home_state`, `slug`, `sort_order`, and matching lists `states`, `counties`, `cities`) is filled by `sync_venues_from_gsheets` from the sheet's `geo-filters_json` tab, which replaces all areas each day. Matching is `core/geo_filters.py`: `area_q` (state, and county or city), `metro_groups` (metros grouped by `home_state` for the dropdown's `<optgroup>`s), `metro_towns`, `town_neighborhoods`, `parse_geo_filter` (unknown slugs dropped), `geo_filter_context` (shared by the listing and the discovery deck). Since `limit-listings-to-new-england`, only New England areas are offered.
- Massachusetts has 240 venues (226 active): Middlesex 85, Suffolk 44, Worcester 26, Essex 23, Hampshire 18, Norfolk 11, Franklin 9, Plymouth 9, Bristol 7, Hampden 3, Barnstable 3, Berkshire 2. Only 14 give their town as "Boston"; the rest of Suffolk give a neighborhood as their town ("Allston", "Jamaica Plain"). OpenStreetMap's neighborhood names (`Venue.neighborhood`) don't always match the editors' ("Fenway-Kenmore", "Downtown Crossing").
- Venue IDs are `V0001`…`V0729`; `Venue.sheet_id` is unique but nullable, so the admin can already add a venue with no ID.
- Patterns already in the code for data kept in step on every migrate: `core/site_record.py` and `core/admin_group.py` (a `post_migrate` handler).

## Goals / Non-Goals

**Goals:**
- Areas reviewable and changeable in one file, with comments, under version control.
- Every Massachusetts venue in exactly one sub-region, by rules an editor can read in that file.

**Non-Goals:**
- Pickable groups (a whole group as a filter); groups are headings only.
- Sub-regions for other states (their metros are copied as they are).
- Deleting `sync_venues_from_gsheets` or the service account; they stay for a manual import.
- Re-geocoding venues or fixing their counties.

## Decisions

### 1. One data file, loaded on every migrate
`core/geo_areas.py` holds `AREAS`, a list of dicts in display order (`key`, `kind`, `label`, `home_state`, `group`, `states`, `counties`, `cities`, `neighborhoods`, `default_counties`). A `post_migrate` handler (`core/geo_area_sync.py`, like `site_record.py`) makes `GeoArea` match it: creates, updates, and deletes areas not in the file, keyed by `key` stored in the existing `sheet_id` column (existing keys such as `metro_NH_South` kept, so nothing else moves). Python, not JSON or YAML, so editors' notes sit beside the rules and no parser is added.
*Alternatives:* a data migration (rejected: every later edit would need another migration); keeping the sheet for areas (rejected by the decision to retire the sheet).

### 2. Two new GeoArea fields
`group` (the heading, "Western Massachusetts"; blank for other areas) and `neighborhoods` and `default_counties` (lowercased lists). One schema migration. `metro_groups` groups by `group` when set and by state otherwise, so other states' dropdown is unchanged.

### 3. Exactly one sub-region per Massachusetts venue, by construction
For a Massachusetts sub-region, `area_q` becomes: state MA and (town in its `cities` **or** (town is Boston and neighborhood in its `neighborhoods`) **or** (county in its `default_counties` and the venue matched no sub-region's town or neighborhood)). "Matched no sub-region's town or neighborhood" is built once from the whole file (every sub-region's cities, and Boston plus every neighborhood), so a county default can't claim a venue a listed town already placed. A test asserts every active Massachusetts venue with a county matches exactly one sub-region, against fixtures and, as a report command, against real data (task 4.2).
Names the editors wrote with alternatives become several entries: "Allston-Brighton" → `allston`, `brighton`; "Barnstable/Hyannis" → `barnstable`, `hyannis`; "Tisbury/Vineyard Haven" → `tisbury`, `vineyard haven`; "Gosnold / Cuttyhunk" → both; "Manchester-by-the-Sea" → also `manchester`; Boston neighborhoods that venues give as their town (Allston, Brighton, Dorchester, Jamaica Plain, Roxbury, Roslindale, West Roxbury, Hyde Park, Mattapan, Charlestown, East Boston, South Boston) are listed in `cities` too; OpenStreetMap's spellings are added to `neighborhoods` (`fenway-kenmore` with Fenway, `downtown crossing` with Downtown).

### 4. County defaults
Each Massachusetts county has one default sub-region, for venues in towns the editors didn't list:

| County | Default sub-region |
|---|---|
| Berkshire | The Berkshires |
| Franklin, Hampshire, Hampden | Pioneer Valley / Connecticut River Valley |
| Worcester | Greater Worcester |
| Middlesex | MetroWest |
| Essex | North Shore |
| Suffolk | Downtown & Central Boston (a Boston venue with no neighborhood, or one not listed) |
| Norfolk | Metro South / Greater Brockton |
| Plymouth | South Shore |
| Bristol | South Coast |
| Barnstable | Mid-Cape |
| Dukes | Martha's Vineyard |
| Nantucket | Nantucket |

Middlesex is split five ways by the editors' lists, so its default will carry unlisted towns (Woburn, Lexington, Burlington…); the report in task 4.2 lists every venue a default placed, for the editors to add towns where the default is wrong.

### 5. Labels and addresses
Sub-region labels are "MA: <name>" (`short_label` drops "MA: " in the grouped dropdown), so their URL values follow the existing rule: `ma-the-berkshires`, `ma-north-of-the-charles`, `ma-downtown-central-boston`. The old slugs map to the state in `parse_geo_filter`, apart from `ma-north-shore`, which the new North Shore ("MA: North Shore") takes over, keeping its Essex County venues, before unknown values are dropped (an `OLD_METRO_SLUGS` set beside `AREAS`); the listing, the remembered filter and `/calendar.ics` all go through it.

### 6. The other areas are copied as they are
The current regions, states and non-Massachusetts metros are written into `AREAS` from the stored areas (read from production, which the daily sync last filled), in their current order and with their keys, so nothing outside Massachusetts changes. The New England-only offering stays as it is.

### 7. The sheet sync stops
`bin/daily.sh` drops its `sync_venues_from_gsheets` step. The command loses its geo-tab step and `--geo-tab` option; it still imports venues by hand, `--dry-run` first. `VenueAdmin.save_model` gives a new venue with no ID the next `V` number (max numeric part + 1, padded to four digits); the model's uniqueness already refuses a duplicate.

## Risks / Trade-offs

- **Saved links and bookmarks to old metros** widen to all of Massachusetts rather than the old area; better than every area, but a Cape Cod subscriber now gets Boston's shows too. The new feeds' links are on the listing for them to resubscribe.
- **County defaults misplace some venues** (Middlesex most); the report makes them visible and the fix is a line in the data file.
- **Venue data quality:** a venue with no county and an unlisted town lands in no sub-region (still in Massachusetts); the report lists those too.
- **Editors lose the sheet as their tool** for areas and venues; areas now change through code review, venues in the admin.
