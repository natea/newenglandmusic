## 1. GeoArea model and membership

- [x] 1.1 Add `GeoArea` to `core/models.py`. Fields: `kind` (`region`, `state`, `metro`), unique `sheet_id`, `label`, `home_state`, `slug`, `sort_order`, and lists `states`, `counties` and `cities` (Postgres `ArrayField`, like `Venue.genres`). Make `kind` + `slug` unique together and order by `sort_order`. Verify that `makemigrations` creates one migration and that `migrate` applies it.
- [x] 1.2 Add `core/tests/fixtures/geo_filters.json`, a trimmed copy of the `geo-filters_json` tab. It needs:
  - the `ALL` row;
  - the regions New England: South, Tri-State and Northeast Corridor (the one with no states);
  - the states Massachusetts, Vermont and Rhode Island;
  - the metros MA: Boston (county + city), MA: Boston Metro Region (city), MA: Cape Cod (county), MA: Central, VT: North and VT: South.

  Verify that it loads as JSON in the same shape `gog --json --results-only` returns.
- [x] 1.3 Create `core/geo_filters.py` with `area_q(area, prefix="")`, which turns an area's rules into a venue `Q` (states AND (counties OR cities), case-insensitive), and `offered_areas(kind)`, which leaves out areas with no states.
- [x] 1.4 Write tests in `core/tests/test_geo_filters.py`, verified when they pass. Cover every scenario of "A venue belongs to an area by the sheet's rules": state-only region, metro by county, metro by county or city, same county name in another state, nested metros, event without a venue. Also cover "Area with no states" and "Sheet order" from "Only areas that can match appear as options".

## 2. Sync areas from the sheet

- [x] 2.1 Extend `sync_venues_from_gsheets`:
  - Read the `geo-filters_json` tab, with `--geo-tab` to override its name.
  - Group rows by `ID` and parse the comma-separated values.
  - Skip the `ALL` row, and warn on and skip unknown filter or match types.
  - Build slugs with `slugify(label)`, and stop with an error on a duplicate slug within a kind.
  - Upsert areas by `sheet_id` and delete areas that are missing, all inside the existing transaction.
  - Fail with an error naming the tab if it can't be read.

  Verify by running the command with `--dry-run` against a mocked `gog`.
- [x] 2.2 Extend the dry run and the summary to report areas added, updated and removed, plus the number of venues in no metro, per state. Verify with a test of the command's output.
- [x] 2.3 Write tests in `core/tests/test_sync_venues_from_gsheets.py`, mocking `get_rows_from_google_sheets` per tab with the fixture, verified when they pass. Cover the scenarios metro with several rules, area removed from the sheet, unknown filter or match type, missing tab (where neither venues nor areas change), and the modified dry-run scenario (counts reported, nothing saved). Check that the existing sync tests still pass.
- [x] 2.4 Update the module docstring of `sync_venues_from_gsheets` to say that it also syncs areas from `geo-filters_json`. Verify by reading the docstring.

## 3. Filter the public events listing

- [x] 3.1 Add `parse_geo_filter(querydict)` to `core/geo_filters.py`. It resolves `region`, `state` and `metro` slugs to offered areas, drops unknown slugs, drops a metro whose `home_state` isn't the chosen state, and returns the chosen areas and a query string. Verify with unit tests in `test_geo_filters.py`.
- [x] 3.2 Change `core/views/index.py` so that `_get_events_page_for_month` parses the filter and `_fetch_events_from_start_to_end_time_group_by_date_as_list` ANDs each area's `Q` (with the `venue__` prefix). Pass the options, the selection and the query string to the template. Verify with the tests in 3.5.
- [x] 3.3 Add the filter form to `core/templates/core/index.html`:
  - three selects, with metros in one `<optgroup>` per home state and the `XX: ` prefix dropped;
  - a "Filter" submit button;
  - a "no events match these filters" message with a link that clears them, shown when the filter returns nothing;
  - the query string appended to the prev/current/next month links, and to the calendar links in `calendar/calendar.html` that point to other months.

  Verify on the dev server at port 8001.
- [x] 3.4 Add a small inline script that shows only the chosen state's metro optgroup, clears a metro that no longer fits, and submits the form when a select changes. Verify in the browser that choosing Massachusetts limits the metros and reloads the filtered page, and that the form still works with JS disabled.
- [x] 3.5 Write tests in `core/tests/test_index_geo_filter.py`, using the test client with venues, events and areas created in the test, verified when they pass. Cover every scenario of:
  - "Visitors can filter the events listing by region, state and metro area": filter by state, filter by metro area, region and state together (empty-state message), month archive, no filter.
  - "The metro area options follow the chosen state": metros narrowed to the state, metro from another state, state without metros.
  - "Filters survive navigation and bad input": month links keep the filter, unknown value.

  Check that `test_index_page.py` and `test_archive_page.py` still pass.

- [x] 3.6 Add the remembered filter to `_get_events_page_for_month`, following the order in design.md:
  - `clear` or all-empty filter keys: delete the cookie.
  - Valid filter keys: render filtered and set the `geo_filter` cookie (one year, `SameSite=Lax`, `HttpOnly`, `Secure` on HTTPS).
  - No filter keys and a valid cookie: 302 to the same path with the cookie's query string.
  - A stale cookie: delete it.

  Add a "show all" link (`?clear=1`), and make sure the form's "All" options submit empty values. Verify with the tests in 3.7.
- [x] 3.7 Write tests in `core/tests/test_index_geo_filter.py`, verified when they pass. Cover every scenario of "The site remembers a visitor's last filter":
  - filter is remembered
  - remembered filter on a month archive
  - a shared link wins over the cookie
  - clearing the filter, both by choosing "All" and by the "show all" link
  - stale cookie
  - no filter chosen (no `Set-Cookie`, no redirect)
  - search ignores the cookie
- [x] 3.8 On the dev server, verify that choosing Vermont and then opening `/` in the same browser lands on `/?state=vermont`, and that "show all" stops the redirect.

## 4. Admin filters

- [x] 4.1 Add `RegionListFilter`, `StateListFilter` and `MetroListFilter` to `core/admin.py`. They are `SimpleListFilter`s with a `field_prefix` class attribute and the parameter names `region`, `state` and `metro`. `MetroListFilter.lookups()` narrows to the state chosen in `request.GET`. Verify with the tests in 4.3.
- [x] 4.2 Add the three filters to `EventAdmin.list_filter`, which covers both the events list and `/admin/core/alleventproxy/`, with prefix `venue__`. Add them to `VenueAdmin.list_filter` too, replacing the raw `state` entry. Verify in the admin that the sidebar shows the filters and that they combine with "is approved" and Kind.
- [x] 4.3 Write tests in `core/tests/test_admin_geo_filter.py`, logged in as a superuser, verified when they pass. Cover the scenarios review queue for one metro, venues by region, and admin metro list follows the state. Check that `test_event_admin_kind.py` and `test_venue_admin.py` still pass.

## 5. Load real data and check

- [x] 5.1 Run `venv/bin/python manage.py test` with outbound network blocked, and verify the whole suite passes.
- [x] 5.2 Run `sync_venues_from_gsheets --dry-run`, then a real run, logged to `logs/sync_venues_from_gsheets-YYYY-MM-DD.log`. Verify that 53 areas are stored: 7 regions, 12 states and 34 metros, with Northeast Corridor stored but not offered. Verify too that the no-metro counts match the design (RI 37, DC 12, 9 others).
- [x] 5.3 On the dev server, verify that `/?state=massachusetts&metro=ma-boston-metro-region` lists only Boston-area events, that the day map shows only those venues, and that the next-month link keeps the filter.
