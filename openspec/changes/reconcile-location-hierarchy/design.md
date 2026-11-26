# Design

## Context

See proposal.md for why. What shapes the approach:

- **Today's areas are rules, checked on every request.** `core/geo_areas.py` lists each area with states, counties and cities. `core/geo_filters.py` turns them into a query on the venue's `state`, `county`, `city_town` and `neighborhood` text. Massachusetts's sub-regions add town lists, Boston neighborhood lists and county defaults.
- **The editors' file is a different kind of thing:** one row per town (1,602) and per Boston neighborhood (19), each with its state, region and sub-region, plus the Census identifier, kind, county and centre point. It lists every town, so nothing needs a county default.
- **Venues carry free text.** `Venue.city_town` is what the sheet or an editor typed, and `Venue.neighborhood` is OpenStreetMap's name or an editor's.
- **Many things read a filter's query string:** the listing, the remembered-filter cookie, `/calendar.ics`, weekly email area choices (`area_query`), the venue list, the discover page, the venue page's sub-region link and the admin.

What the file and the local copy of the venues (569 New England venues, read on 2026-11-25) show:

| Finding | Number |
| --- | --- |
| Venues whose town text is a town in the file | 530 of 569 |
| Venues whose town text isn't (17 names, all villages or Boston neighborhoods) | 39 |
| Massachusetts venues the file puts in a different sub-region than today's county default | 13 of 240 |
| Massachusetts sub-regions named differently in the file | 5 of 28 |
| Sub-regions in the file, and those with a venue | 117, 78 |
| Regions with a single sub-region | 14 of 50 |
| Vermont sub-region names used under more than one region | 7 |
| Connecticut venues whose county text isn't the file's planning region | 69 of 71 |

Production may differ a little. Task 1.2 reruns these numbers on a copy of production before anything is built on them.

## Goals / Non-Goals

**Goals:**
- One source for the hierarchy, for all six states, that the editors can revise by sending a new file.
- A venue's place is a stored fact an editor can see, correct and export.
- The picker reads the same at every level in every state.
- No link, saved filter, feed or email choice breaks.

**Non-Goals:**
- **Changing what a venue shows.** Events keep the venue's own town text and neighborhood ("Allston, MA").
- **Neighborhood lists for cities other than Boston.** The file has none. Their neighborhoods stay OpenStreetMap's.
- **Pages or addresses for regions and towns** (`/ma/greater-boston/`). The filter keeps using query parameters.
- **Using the file's town centres for distance or maps.** They are stored, and nothing reads them yet.
- **Venues outside New England.** They get no placement.
- **Editing the hierarchy in the admin.** It changes by replacing the file and deploying, like `core/geo_areas.py` today.

## Decisions

### 1. The file is checked in whole, and a small Python file holds what it lacks

The editors' CSV goes to `core/data/stagehopper_regions.csv` unedited, so their next version can replace it and `git diff` shows what moved. `core/place_names.py` holds the three things the file doesn't:

- **Display names** for the seven Massachusetts regions the file writes in capitals ("METROWEST" is "MetroWest").
- **Other names for towns**, each a state, a name and the town it means: those already in `core/geo_areas.py` (Florence, Shelburne Falls, Manchester, Hyannis, Vineyard Haven, Siasconset, Madaket, Cuttyhunk, and the Boston neighborhoods venues give as towns) and the eight more the venues need (Milldale to Southington and Broad Brook to East Windsor, CT; Rumford to East Providence and Chepachet to Glocester, RI; Morrisville to Morristown, Bellows Falls to Rockingham and Waterbury Center to Waterbury, VT; North Woodstock to Woodstock, NH).
- **Other names for listed neighborhoods:** Fenway-Kenmore and Kenmore for Fenway, Downtown Crossing for Downtown, Allston and Brighton for Allston-Brighton.

*Alternative: read the file from a Google Sheet.* Rejected for now. A sheet needs credentials on the server and a sync job, and a bad edit would move venues with no review. A checked-in file is reviewed like code.

*Alternative: put other names in the admin.* Rejected for now. It is a second place to look, and the list is short. The unplaced report tells an editor what to ask for.

### 2. `GeoArea` becomes a tree, and towns and listed neighborhoods get tables

- **`GeoArea`** keeps its name and gains `parent`. Its kinds become `state`, `region` and `sub_region`. `sheet_id` is renamed `key` (such as `MA/GREATER BOSTON/North of the Charles`, built from the file's own names). The rule lists (`states`, `counties`, `cities`, `neighborhoods`, `default_counties`) and `group` are dropped. All twelve states stay as rows, since the admin's State filter lists them.
- **`Town`:** `geoid` (unique), `state`, `name`, `kind`, `county`, `county_geoid`, `latitude`, `longitude`, `sub_region`, and `other_names`.
- **`ListedNeighborhood`:** `town`, `name`, `other_names`, `sub_region`.
- **`Venue`** gains `town`, `listed_neighborhood` and `sub_region` (all nullable, `SET_NULL`), and `placement_source` (blank, or `editor`).

`Venue.sub_region` is stored though it follows from the town and neighborhood, so every filter is one indexed join. Region and state filters go through `sub_region.parent`.

*Alternative: keep rules and generate them from the file.* Rejected. 1,602 town names in `OR` lists per request is slow, and placement would stay invisible to editors.

*Alternative: a new model, leaving `GeoArea` alone.* Rejected. Every reader of `GeoArea` changes anyway, and two area tables would be confusing.

### 3. One function places a venue, and four callers use it

`core/placement.py` has `place(venue)` (returns town, listed neighborhood and sub-region from the venue's state, town text and neighborhood) and `place_venues(queryset)` (applies it with `queryset.update()`, so no event HTML is re-rendered). Callers:

- `Venue.save()` when state, town text or neighborhood changed;
- `sync_venues_from_gsheets`, for the venues it wrote;
- `lookup_venue_neighborhoods`, for the venues whose neighborhood changed;
- the place loader, for every New England venue.

A venue whose `placement_source` is `editor` is skipped by all four. Names are compared with one `normalize` (lowercase, trimmed, hyphens as spaces), and the lookup is a dictionary built once per run from `Town` and its other names.

### 4. The loader checks everything, then syncs in one transaction, on every migrate

`core/place_sync.py` replaces `core/geo_area_sync.py` on `post_migrate`. It parses and validates the whole file first (the faults in `place-hierarchy`), raising one error that lists them all, so a bad file fails the deploy before anything changes. Then, in a transaction, it upserts areas by `key` and towns by `geoid` with bulk operations, deletes what the file no longer lists, and calls `place_venues`. It records a `JobRun` with counts of areas, towns, and venues placed and unplaced. Loading an unchanged file writes nothing.

`check_place_hierarchy <path>` runs the same parse and validation on another file and prints the differences and the venues affected, inside a transaction it rolls back.

### 5. URL values and the parameters

- **Regions:** `<state code>-<region name>`, such as `ma-greater-boston` and `ct-lower-connecticut-river-valley`.
- **Sub-regions:** `<state code>-<name>`, such as `ma-north-of-the-charles`. All 28 Massachusetts sub-regions keep the address their metro had, apart from the five the file renames. Where a state uses one sub-region name under several regions (Vermont), the region's name goes in: `vt-okemo-valley-windham`.
- **Parameters:** `state`, `region`, `subregion`, `town`, `neighborhood`. A sub-region implies its region and state, and a region its state, so the picker shows them selected.

*Alternative: keep the name `metro` for sub-regions.* Rejected. The word is wrong for "Quabbin" or "Northeast Kingdom", and the picker's label, the admin and the URL should say the same thing.

*Alternative: one `area` parameter for either level.* Rejected. A region and its sub-region can share a name (New Hampshire's "Lakes Region"), so one parameter needs a prefix, and two plain menus work without JavaScript.

### 6. Old values are translated in one place

`core/geo_filters.py` gets `LEGACY`, a table built from today's `core/geo_areas.py` before it is deleted:

| Old value | Read as |
| --- | --- |
| `metro=` a Massachusetts sub-region's address (23 unchanged) | the same `subregion` |
| `metro=` one of the 5 renamed (`ma-the-berkshires`, `ma-the-hilltowns`, `ma-pioneer-valley-connecticut-river-valley`, `ma-quabbin-swift-river-valley`, `ma-montachusett-north-county`) | the renamed `subregion` |
| `metro=` an older Massachusetts metro (`ma-boston`, `ma-boston-metro-region`, `ma-cape-cod`, `ma-central`, `ma-south-shore-coast`) | `state=massachusetts` |
| `metro=ma-berkshires` | the sub-region Berkshires (it was read as the state) |
| `metro=` another state's (`ct-coast`, `ct-north`, `me-coast`, `me-north`, `nh-north`, `nh-south`, `vt-north`, `vt-south`) | that state |
| `region=new-england`, `new-england-north`, `new-england-south` | all six states, or ME, NH and VT, or CT, MA and RI |
| `town=` another name for a town | that town, and its listed neighborhood if it names one |

`parse_geo_filter` applies the table first, so the listing, the cookie, the feed and the digest all get it. The cookie is rewritten in the new form the next time the visitor opens a listing. A data migration rewrites each stored weekly email `area_query` through the same table, because the digest treats a choice whose stored string isn't its canonical form as "no longer listed".

### 7. The picker stays a plain form

`core/geo_filter_form.html` keeps its shape: `<select>`s in a GET form, submitted on change by its small script. It gains a Region select (grouped by state when no state is chosen) and renames the metro select to Sub-region, shown only when the chosen region offers two or more. The script clears the menus below the one that changed. `town_chips.js` is unchanged.

"Offered" means at least one active venue. The counts come from one grouped query per page, on `Venue.sub_region`.

### 8. Areas outside New England are removed

The admin's Region and Metro Area filters today also list Tri-State, "NY: Hudson Valley" and other areas the public site never offers. Keeping them means keeping the whole rule engine for venues nobody browses. They are removed with it. The State filter still lists every state.

### 9. Order with the other changes in flight

`add-venue-list` and `add-venue-pages` are built and unarchived, and `add-weekly-email-digest` and `add-search-results-map` are open. Their specs name the metro filter (`/?metro=ma-north-of-the-charles` on the venue page, "a region, state or metro area" in the email form, and a change to "The site remembers a visitor's last filter"). This change:

- doesn't touch "The site remembers a visitor's last filter", so `add-venue-list`'s delta still applies cleanly;
- should be built after `add-venue-list` and `add-venue-pages` are archived, and its first task updates their archived specs' wording where it names a metro;
- updates the digest's form options in code, and `add-weekly-email-digest`'s spec in the same pull request if it is still open.

### Tests

**No external service is called by anything in this change,** so nothing new is mocked. The file is local, and the Census data is already in it.

- **Small fixture:** `core/tests/place_fixture.py` writes a short regions CSV (a few towns in three states, Boston with four neighborhoods, a Vermont name used twice) to a temporary file, and tests point the loader at it.
- **The real file:** one test loads `core/data/stagehopper_regions.csv` and asserts its invariants (1,602 towns, 19 listed neighborhoods, every town in one sub-region, every URL value unique), so a bad new version fails CI.
- **OpenStreetMap:** tests of `lookup_venue_neighborhoods` re-placing venues keep using `core/tests/osm_fixture.py` for Nominatim and Overpass.
- **Google Sheets:** tests of `sync_venues_from_gsheets` re-placing venues keep mocking `gog`.
- **The picker:** Django test-client tests for the no-JavaScript form, and one Playwright test for the cascade and the chips.

## Risks / Trade-offs

- **[A venue with an unknown town text drops out of its region]** → It still shows under its state. The loader's `JobRun` records the unplaced count, `report_unplaced_venues` lists them, and task 1.2 gets the count to zero on a production copy before deploy.
- **[About 13 Massachusetts venues change sub-region]** → That is the editors' intent. `check_place_hierarchy` prints the list, and the owner sees it before G4.
- **[Vermont's list looks unfinished]** → Seven sub-region names sit under several regions, and some sub-regions hold one town. It is loaded as given. The picker hides a Sub-region menu with fewer than two offered choices, so most of it never shows. The editors are asked to review it (open question 1).
- **[Old addresses are many]** → One table, with a test per row kind, and a test that every `metro` slug the site offered before resolves to something.
- **[The loader runs on every migrate]** → It diffs before writing, so an unchanged file costs one read of two tables.
- **[A Boston venue whose OpenStreetMap neighborhood isn't a listed one]** → It stays in Boston's default sub-region, as today, and the report lists it so an other name can be added.
- **[Two sources of truth for a venue's town: its text and its matched town]** → Deliberate. The text is what the venue calls itself, and the match is where it is. The admin and the export show both side by side.

## Migration Plan

1. **Before building:** restore a production backup locally, and run the numbers in Context on it (task 1.2).
2. **Schema migration:** add `GeoArea.parent`, `Town`, `ListedNeighborhood` and the `Venue` fields; rename `sheet_id` to `key`.
3. **Load:** `post_migrate` loads the file and places every venue.
4. **Data migration:** rewrite stored weekly email `area_query` values through `LEGACY`.
5. **Second schema migration:** drop `GeoArea`'s rule lists and `group`, and delete the old metro and multi-state region rows.
6. **Deploy** is one push. Render's build runs `migrate`, which does steps 2 to 5.
7. **After deploy:** run `report_unplaced_venues` on production and send the editors the list.

**Rollback:** revert the commit and migrate back. The old areas reload from `core/geo_areas.py` on that migrate. Weekly email choices rewritten to `subregion=` would read as "no longer listed" on the old code, so the data migration's reverse rewrites them back for the 23 unchanged addresses.

## Open Questions

1. **Vermont's regions and sub-regions.** Should the editors revise them before or after this ships? It doesn't change the build: a revised file is a new file.
2. **Who checks the eight new village names?** They are from general knowledge, and an editor who knows the towns should confirm them.
