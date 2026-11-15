# Tasks

## 1. Areas in the code

- [x] 1.1 Add `group`, `neighborhoods` and `default_counties` to `GeoArea` with a migration; verify `makemigrations --check` is clean and the migration applies.
- [x] 1.2 Write `core/geo_areas.py`: the current regions, states and non-Massachusetts metros copied from production's stored areas (read only) in their order and with their keys, then the 28 Massachusetts sub-regions in seven groups with the editors' towns, Boston neighborhoods and aliases, and the county defaults (design Decisions 3 and 4), plus `OLD_METRO_SLUGS`; verify a test that every sub-region has a group, a label starting "MA: ", towns or neighborhoods, and that each Massachusetts county has exactly one default.
- [x] 1.3 Add the `post_migrate` sync (`core/geo_area_sync.py`) that makes `GeoArea` match `AREAS` (create, update, delete, keyed by `key`); verify with tests that a new area is added, a changed one updated, a removed one deleted, and that running it twice changes nothing.

## 2. Matching and the filter

- [x] 2.1 Teach `area_q` the sub-regions' rules (town, Boston neighborhood, county default only for venues no town or neighborhood placed); verify "A listed town", "A Boston neighborhood", "A town the list doesn't name", "Every venue placed", and the modified matching scenarios ("Metro matched by county", "Metro matched by county or city", "Same county name in another state", "Nested metros").
- [x] 2.2 Group the Metro Area options by `group` for Massachusetts (`metro_groups`), keeping other states grouped by state; verify "Metros narrowed to the state" and the admin's "Review queue for one metro".
- [x] 2.3 Map `OLD_METRO_SLUGS` to the state in `parse_geo_filter`; verify "An old listing link", "A subscribed feed" and "The North Shore address kept", and that a remembered filter cookie holding an old slug redirects to Massachusetts.
- [x] 2.4 Update the towns and neighborhoods tests to the sub-regions (`ma-north-of-the-charles`, `ma-downtown-central-boston`); verify every scenario of "Visitors can narrow a metro area to some of its towns" and "…to some of their neighborhoods", and the calendar feed's "Metro feed".

- [x] 2.5 Drop the Region menu from the filter form (the `region` parameter still applies), and for a metro with one town offer no town filter but that town's neighborhoods; verify "No region menu", "A metro with one town", and the modified neighborhood scenarios ("Two neighborhoods", "No town chosen").

## 3. The sheet sync stops

- [x] 3.1 Remove the sync's area step (and its geo-tab option) and its tests, and drop `sync_venues_from_gsheets` from `bin/daily.sh`; verify "Not in the daily job", the daily job's "Daily run" (eight commands), and that the sync's remaining tests (venue tab only, service account, errors) pass with the modified scenarios.
- [x] 3.2 Give a venue added in the admin with no ID the next `V` number; verify "The next ID", "A duplicate ID" and "An edit stays" with admin tests.

## 4. Check it on real data

- [x] 4.1 Run the whole suite with the network blocked and verify it passes, with every scenario in this change's specs covered by a test.
- [ ] 4.2 Add a `report_massachusetts_regions` command (each sub-region's venue count, and the venues placed by a county default or by none), run it against a copy of production's venues locally, and send the editors its list of default-placed and unplaced venues; verify every active Massachusetts venue with a county is in exactly one sub-region.
- [x] 4.3 Check the filter on the local site at 1440px and 390px: the grouped Metro Area options, choosing North of the Charles then Somerville, and Downtown & Central Boston then a neighborhood.

## 5. Finish

- [x] 5.1 Update `AGENTS.md` (venues kept in the admin, areas in `core/geo_areas.py`, the sync manual only) and `PRODUCTION.md` (the daily job, how to change an area, the old metro addresses); verify both describe the shipped behavior.

## Workflow follow-up

- After the deploy, check the live filter's Massachusetts options and an old `/calendar.ics?metro=ma-cape-cod` feed.
- Archive with `/opsx:archive add-massachusetts-regions` once every task is ticked and every scenario has a passing test.
