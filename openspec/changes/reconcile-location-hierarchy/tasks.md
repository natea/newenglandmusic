# Tasks

## 1. Before building

- [ ] 1.1 Archive `add-venue-list` and `add-venue-pages`, or merge `main` into this branch after they are; verify `openspec list` no longer shows them and that `openspec/specs/venue-pages/spec.md` exists
- [ ] 1.2 Restore a production backup into a scratch database and rerun the counts in design.md's Context table against it; record the production numbers in design.md, and verify the list of unmatched town texts is covered by design decision 1's other names (add any that aren't)
- [ ] 1.3 Send the owner the production list of Massachusetts venues that change sub-region and the Vermont question (design.md, open question 1); verify a reply is recorded in design.md before task group 6

## 2. The list of places

- [ ] 2.1 Add `core/data/stagehopper_regions.csv` (the editors' file, unedited) and `core/place_names.py` (display names, other names for towns and for listed neighborhoods); verify the file's SHA-256 matches the editors' copy
- [ ] 2.2 Schema migration: `GeoArea.parent`, the `sub_region` kind, `sheet_id` renamed `key`; new `Town` and `ListedNeighborhood` models; verify `makemigrations --check` is clean and `migrate` runs on a copy of the current database
- [ ] 2.3 Write `core/place_sync.py`: parse and validate the whole file, then sync areas, towns and listed neighborhoods in one transaction, with display names and URL values; wire it to `post_migrate` in place of `core/geo_area_sync.py`; verify a second `migrate` reports nothing changed
- [ ] 2.4 Add `core/tests/place_fixture.py` (a short regions file: three states, Boston with four neighborhoods, a Vermont sub-region name used under two regions)
- [ ] 2.5 Tests for `place-hierarchy` "The site keeps one list of places", "A town carries its Census details" and "Editors can list a town's neighborhoods" (7 scenarios); verify they pass
- [ ] 2.6 Tests for "Places have other names" and "Areas have display names and stable addresses" (7 scenarios, including the two-towns clash and the Vermont URL values); verify they pass
- [ ] 2.7 Tests for "A file with a fault is refused whole" and "The site's places always match the file" (5 scenarios, each asserting that a refused file changes no row); verify they pass
- [ ] 2.8 Test that loads the real file and asserts 1,602 towns, 19 listed neighborhoods, one sub-region per town and unique URL values; verify it passes
- [ ] 2.9 Add `check_place_hierarchy <path>` (faults, differences and affected venues, changing nothing) with tests for its 2 scenarios; verify the tests pass and that running it on the checked-in file reports no difference

## 3. Venue placement

- [ ] 3.1 Schema migration: `Venue.town`, `Venue.listed_neighborhood`, `Venue.sub_region` and `Venue.placement_source`; verify `makemigrations --check` is clean
- [ ] 3.2 Write `core/placement.py` (`place` and `place_venues`, saving with `queryset.update()`), and call it from the place loader; verify every New England venue in the local database gets a placement or appears in the unplaced count
- [ ] 3.3 Tests for `venue-placement` "A venue is matched to a town in the list", "A venue in a town with listed neighborhoods is matched to one" and "A placed venue is in exactly one sub-region and region" (12 scenarios); verify they pass
- [ ] 3.4 Re-place venues in `Venue.save()` (when state, town text or neighborhood changed), `sync_venues_from_gsheets` and `lookup_venue_neighborhoods`, skipping editor-set placements
- [ ] 3.5 Tests for "Placement follows changes to the venue and to the list" (4 scenarios; the sheet with `gog` mocked, OpenStreetMap from `core/tests/osm_fixture.py`, and an assertion that event HTML isn't re-rendered); verify they pass
- [ ] 3.6 Venue admin: show the matched town, listed neighborhood, sub-region and region; let an editor choose the town and neighborhood (autocomplete) or clear them; add the "no matched town" filter
- [ ] 3.7 Tests for "Editors can see and correct a venue's placement" (3 scenarios) and "What a venue shows is unchanged" (1 scenario); verify they pass
- [ ] 3.8 Replace `report_massachusetts_regions` with `report_unplaced_venues`, and record placed and unplaced counts on the loader's `JobRun`; tests for "Unplaced venues are reported" (3 scenarios); verify they pass

## 4. Filtering by the hierarchy

- [ ] 4.1 Rewrite `core/geo_filters.py`: membership by `Venue.sub_region` and its parents, the `state`, `region` and `subregion` parameters, implied parents, offered areas (at least one active venue, from one grouped query), and towns and neighborhoods from `Venue.town` and `Venue.listed_neighborhood`
- [ ] 4.2 Tests for `event-geo-filter` "A venue belongs to an area by its placement", "Visitors can filter the events listing by state, region and sub-region" and "The region and sub-region are remembered like the state" (12 scenarios); verify they pass
- [ ] 4.3 Tests for "Each menu follows the choice above it" and "Only areas with venues appear as options" (12 scenarios); verify they pass
- [ ] 4.4 Tests for "Visitors can narrow an area to some of its towns" and "Visitors can narrow chosen towns to some of their neighborhoods" (13 scenarios); verify they pass
- [ ] 4.5 Add the `LEGACY` table (design decision 6), built from today's `core/geo_areas.py`, and apply it in `parse_geo_filter`
- [ ] 4.6 Tests for "Old addresses still work" (7 scenarios), plus a test that every `metro` and `region` URL value the site offered before this change resolves to an area or a state; verify they pass
- [ ] 4.7 Verify the existing tests of "Filters survive navigation and bad input" and "The site remembers a visitor's last filter" still pass unchanged, apart from fixtures that built areas from rules

## 5. The picker, the admin and the other readers

- [ ] 5.1 Update `core/templates/core/geo_filter_form.html` and its script: State, Region, Sub-region (only with two or more offered), towns and neighborhoods, each cleared when a menu above it changes
- [ ] 5.2 Django test-client tests of the form without JavaScript (menus shown and hidden, selected values, "Without JavaScript" town scenario), and one Playwright test of the cascade and "Towns are chosen as chips" (2 scenarios); verify they pass after `compilescss`
- [ ] 5.3 Admin: State, Region and Sub-region sidebar filters on the event, all-events and venue lists; tests for "Admins can filter events and venues by state, region and sub-region" (4 scenarios) and `new-england-scope` "Nothing is deleted, and the admin opens on New England" (7 scenarios); verify they pass
- [ ] 5.4 Calendar feed and subscribe links: take `region` and `subregion`; tests for `area-calendar-feeds` "Feeds follow the list of places" (5 scenarios); verify they pass and the existing feed tests still pass
- [ ] 5.5 Weekly email: offer regions and sub-regions in the area choices (`core/digest_forms.py`), and write the data migration that rewrites stored `area_query` values through `LEGACY`, with its reverse; test the migration forwards and backwards on a metro choice, a metro-and-towns choice and another state's old metro; verify they pass
- [ ] 5.6 Venue page and venue list: read the sub-region from `Venue.sub_region` for every state and link it with `subregion=`; update their tests and the wording of their archived specs where they name a metro; verify the tests pass
- [ ] 5.7 Venue export: add the matched town, listed neighborhood, sub-region, region and placement source columns; tests for `venue-export` "The file shows where the site places each venue" (2 scenarios); verify they pass
- [ ] 5.8 Discover page: verify its filter form shows the new menus and its existing tests pass

## 6. Removing the old areas

- [ ] 6.1 Second schema migration: drop `GeoArea`'s `states`, `counties`, `cities`, `neighborhoods`, `default_counties` and `group`, and delete the old metro and multi-state region rows; verify `migrate` and its reverse both run on a copy of the current database
- [ ] 6.2 Delete `core/geo_areas.py` and `core/geo_area_sync.py`, and remove every import of them; verify `grep -rn "geo_areas\|geo_area_sync\|report_massachusetts_regions" core bin` finds nothing outside migrations
- [ ] 6.3 Update `AGENTS.md` ("Data sources": the regions file, how to check and adopt a new version, `report_unplaced_venues`) and `PRODUCTION.md`; verify the commands they name run as written

## 7. Whole-change checks

- [ ] 7.1 Run `venv/bin/python manage.py compilescss` then `venv/bin/python manage.py test` with outbound network blocked; verify the whole suite passes
- [ ] 7.2 Run `check_place_hierarchy` and `report_unplaced_venues` on a production copy with the new code; verify no active New England venue is unplaced, or record each one left in design.md with the reason
- [ ] 7.3 Run `openspec validate reconcile-location-hierarchy --strict`, and verify every scenario in the six delta specs has a named passing test

## Workflow follow-up

- After deploy, run `report_unplaced_venues` on production and send the editors the list.
- Archive the change once the owner accepts the implementation (G4).
