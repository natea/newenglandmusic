## Context

- **Venue location data:** each `Venue` stores `state` (2-letter), `county` and `city_town`, all synced from the sheet.
- **How the sheet defines areas:** the sheet's `geo-filters_json` tab defines every region, state and metro area. It has 96 rows, which make up 7 regions, 12 states and 34 metros, plus an `ALL` row. Each row has the columns `FILTER_TYPE`, `ID`, `LABEL`, `STATE`, `MATCH_TYPE` and `VALUES`. An area spans one or more rows, one rule per row:
  - regions and states: one `state` rule
  - metros: a `state` rule, plus `county` and/or `city` rules
- **Where the dropdowns come from:** the `PARAMETERS` tab holds the dropdown lists that the Music Map shows (the screenshots in the request). They're the same areas without the matching rules, so `geo-filters_json` is the one source to read.
- **Coverage against the current 729 venues** (checked locally):
  - 671 venues belong to at least one metro.
  - 132 belong to more than one, because metros nest: "MA: Boston" sits inside "MA: Boston Metro Region".
  - The 58 with no metro are the 37 Rhode Island venues (the sheet has no RI metros), the 12 DC venues (county `-`), and 9 others whose county isn't in any metro's list.
- **How the listing works today:** both the homepage and the month archive go through `_get_events_page_for_month` in `core/views/index.py`. The day maps (`map/map.html`) read event coordinates from the rendered event `div`s, so they follow whatever the view renders.
- **Admin today:** `EventAdmin` backs both admin event lists, and already uses `SimpleListFilter`s (`StartTimeListFilter`, `KindListFilter`). `VenueAdmin` filters on the raw `state` field.

## Goals / Non-Goals

**Goals:**
- Read the geography from the sheet. Changing an area's counties, or adding a metro, should take a sheet edit and a sync, not a code change.
- Use one membership rule for the site, the admin events lists and the admin venue list.

**Non-Goals:**
- **Search:** results from `?s=` are not filtered.
- **Other filters:** the Music Map's Location Type, Open Mic, Open Gigs, Genre and Map Focus filters are out of scope.
- **Remembering filters in the admin:** Django's own `_changelist_filters` already keeps an admin's filters while they move between list and edit pages, and that's enough. The admin gets no cookie.
- **Server-side profiles:** the remembered filter lives only in the visitor's cookie. Nothing is stored per visitor in the database or a session.
- **Matching by location:** areas are matched on the sheet's state, county and city, never on Places coordinates or a geographic radius.
- **Fixing sheet data in code:** the DC county `-` and the "Pennslyvania" misspelling should be fixed in the sheet copy.

## Decisions

### Store areas in one `GeoArea` model with rules as array fields

`GeoArea` has these fields:
- `kind`: region, state or metro
- `sheet_id`: the tab's `ID`, unique
- `label`
- `home_state`: the tab's `STATE` column, used for metros only
- `slug`: unique within a kind
- `sort_order`
- `states`, `counties` and `cities`: Postgres `ArrayField`s, like `Venue.genres`, normalized to lowercase and trimmed

Rules are stored inline because an area has at most three short lists. A separate rule table would mean an extra join for nothing.

*Alternative:* hard-code the lists in Python. That's rejected, because the user maintains them in the sheet.

### Work out membership in the query, rather than storing it

`core/geo_filters.py` turns a `GeoArea` into a `Q` on venue fields:
- the states, as `state__in` with uppercase codes, ANDed with
- the counties OR the cities, each value compared with `__iexact`.

For events, the same `Q` is built with a `venue__` prefix. Multiple chosen areas are ANDed together.

*Alternative:* a `Venue.geo_areas` many-to-many, filled in at sync. That's rejected for two reasons:
- It goes stale whenever venues or areas change, unless every write path recomputes it.
- `Venue.save()` re-renders every event's HTML, so maintaining the table through it would be costly.

At 729 venues, and with metro lists of about 50 values at most, the `iexact` OR chain is cheap.

### Slugs come from labels

Slugs are made with `slugify(label)`: `MA: Boston Metro Region` becomes `ma-boston-metro-region`, `New England: North` becomes `new-england-north`, and `Vermont` becomes `vermont`.

Metro labels already start with their state, so their slugs are unique. Labels are what a person reads in a URL. The sheet IDs, such as `metro_MA_South_Shore_/_Coast`, contain a slash and mixed case, so they would make poor URL values.

The sync rejects the whole sync, with an error, if two areas of the same kind produce the same slug.

### Sync the tab in the existing `sync_venues_from_gsheets`

The command reads the `geo-filters_json` tab with the same `gog sheets get … --json --results-only` call it already uses, through `get_rows_from_google_sheets`. It then replaces the areas inside the venue transaction:
- areas are upserted by `sheet_id`
- areas missing from the tab are deleted
- the `ALL` row is skipped

`--geo-tab` overrides the tab name, as `--tab` does for venues.

The "never delete" rule covers venues only. Areas are configuration, and a removed area must stop being offered.

*Alternative:* a separate `sync_geo_areas` command. That's rejected, because it adds a step to the pipeline that's easy to forget, and the two tabs come from the same sheet.

### Filters are a GET form on the listing pages

`index.html` gets a `<form method="get">` with three `<select>`s and a "Filter" button.
- **Metro select:** uses one `<optgroup>` per home state, and the option text drops the `XX: ` prefix.
- **A little inline JS:**
  - hides the optgroups that don't belong to the chosen state;
  - clears a metro that no longer fits;
  - submits the form when a select changes.
- **Without JS:** the select shows every metro, and the server ignores a metro that doesn't fit the chosen state (see the spec).

The view parses the parameters with a single `parse_geo_filter(request.GET)` that returns the resolved areas. Unknown slugs drop out. The function also returns a query string, which the template appends to the month links, and to the calendar links that point to other months.

The view passes the areas to `_fetch_events_from_start_to_end_time_group_by_date_as_list`, which adds the `Q`. The calendar's event dates and the day maps are built from the same query.

### The remembered filter is a cookie that triggers a redirect

The cookie `geo_filter` holds the resolved filter's query string, for example `state=massachusetts&metro=ma-boston-metro-region`. It's set with `max_age` of one year, `SameSite=Lax`, `HttpOnly`, and `Secure` when the request is secure. Only slugs that resolved are written, so the cookie never stores what a visitor typed.

`_get_events_page_for_month` handles the cookie in this order:
1. **`s` is present:** the request is a search, and `index()` hands it off before any of the steps below, as it does today.
2. **`clear` is present, or the filter keys are all present but empty:** delete the cookie and render unfiltered. The "show all" link is `?clear=1`, and the form's "All" options submit empty values.
3. **Any filter key is present:** parse it. If something resolves, render filtered and set the cookie. If nothing resolves, render unfiltered.
4. **No filter keys:** if the cookie parses to a filter, return a 302 to the same path with the cookie's query string. Otherwise, delete any cookie and render unfiltered.

Step 4 can't loop. The redirect target carries filter keys, so it's always handled by step 3.

*Alternative: apply the cookie in place, with no redirect.* That's rejected for three reasons:
- The URL wouldn't show what's being filtered, so a copied link would show the sharer's filter to nobody else.
- A visitor couldn't tell from the address bar why events were missing.
- A future page cache or CDN would need `Vary: Cookie`, and filtered and unfiltered pages would share one URL.

With the redirect, each URL always renders the same way, whatever cookie the visitor has.

*Alternative: `localStorage` and a client-side redirect.* That's rejected because the page would first render unfiltered and then jump, and it wouldn't work without JS.

### The admin gets three `SimpleListFilter`s, shared by both admins

`RegionListFilter`, `StateListFilter` and `MetroListFilter` take the `venue__` field prefix as a class attribute:
- `EventAdmin` uses `venue__`
- `VenueAdmin` uses no prefix, and replaces its raw `state` filter with `StateListFilter`

`MetroListFilter.lookups()` reads the state filter's parameter from `request.GET`, so that it lists only that state's metros.

The filters' parameter names are `region`, `state` and `metro`, the same as the site's. That way an admin URL and a site URL read the same.

## Risks / Trade-offs

- **[Sheet data gaps leave venues outside a metro]**
  - Those venues still match their state and region.
  - The sync's summary reports how many venues belong to no metro, per state, so gaps show up after each sync.
  - Known gaps go in the proposal for the user to fix in the sheet copy.
- **[A sheet edit renames a label]**
  - The slug changes, and old shared URLs stop applying that filter. They fall back to unfiltered, which doesn't break anything.
  - This is acceptable for a local tool. Slugs aren't stored anywhere else.
- **[Region and state can contradict]** (New England plus New York)
  - The result is an empty listing with a "no events match" message and a reset link. The page doesn't silently drop one of them.
- **[A remembered filter hides events and the visitor forgets why]**
  - The redirect puts the filter in the URL, and the form shows it as selected.
  - The "no events match" message and the "show all" link are always one click away.
- **[Every return visit to `/` costs an extra round trip]**
  - It's one 302 with no database queries beyond the area lookup. That's acceptable.
- **[Cookie rules]**
  - It's a strictly functional preference cookie, set only after the visitor chooses a filter, so no consent banner is planned.
  - If the site later adds a privacy page, it should list `geo_filter`.
- **[`StartTimeListFilter` and `KindListFilter` already set defaults on the admin list]**
  - The new filters have no default, so the existing behavior is unchanged.

## Testing

No test touches the network:
- **Google Sheets (`gog`):** tests mock it as `test_sync_venues_from_gsheets.py` does today, either by patching `get_rows_from_google_sheets` (now called once per tab) or by patching `subprocess.run` with canned `--json` output.
- **Recorded fixture:** a small `core/tests/fixtures/geo_filters.json` holds a trimmed copy of the tab, with a region, a state and metros that use state-only, county-only and county-plus-city rules, so the membership tests run against real rows. The tab holds no secrets.
- **Other services:** no other external services are involved.
- **Listing and admin tests:** these use Django's test client, with venues and events created in the test.
- **Cookie tests:** these set the cookie with `self.client.cookies` and check `response.cookies["geo_filter"]` (its value, `max-age`, and deletion) and the redirect `Location`.

## Migration Plan

1. Add the `GeoArea` migration. It adds a table and changes no existing rows.
2. Run `sync_venues_from_gsheets --dry-run`, then a real run, to load the areas.
3. Until that sync runs, no options are offered and the listing is unfiltered.

Rollback: revert the commit and the migration. `Venue` and `Event` are untouched.
