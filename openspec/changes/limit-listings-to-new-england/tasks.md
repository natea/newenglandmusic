Issue: [#58 Remove non-New England regions and states from the homepage search functionality](https://github.com/natea/newenglandmusic/issues/58)

## 1. Scope list and event filter

- [x] 1.1 Add the New England state list and the shared event filter helper, and apply it in the homepage and month listings (event list, calendar dates, day maps); verify with tests for "Listing hides a New York show", "Event without a linked venue" and "Widening the list".
- [x] 1.2 Apply the filter in site search and its suggestions, the calendar feeds, saved shows, act and band pages, the A–Z act index and act suggestions' next-show dates, the discover page (on the inner `Event.objects` queryset in `upcoming_performances()`, not the outer performance query) and the sitemap (the helper must work on its annotated month query); leave `core/spotify_links.py` alone; verify with tests for "Search hides a New Jersey show", "Calendar feed outside New England", the "area-calendar-feeds" scenarios (State feed, Metro feed, Whole Northeast, Remembered filter ignored, Unknown area), "Act page", "Next-show dates", "Saved shows", "Discover", "Search suggestions" and "Sitemap months".
- [x] 1.3 Verify the admin and pipeline are unaffected with tests for "Admin and data untouched", "Fetching continues" and "Artist matching unchanged".

## 2. Search choices

- [x] 2.1 Add `new_england_only` to `offered_areas` and `parse_geo_filter`, comparing states case-insensitively; pass it from the site's callers (index options, `metro_groups`, `geo_filter_for_request`, the calendar feed) and not from `core/admin.py`; verify with tests for "Regions outside New England", "States outside New England", "Metros of removed states", "Area with no states", "Sheet order", "Lowercase sheet states" and "Admin sidebar keeps every area", plus a `town=` link under the flag and a venue with a lowercase state.
- [x] 2.2 Verify old links, cookies and feeds with tests for "Old link to New York", "Old cookie" and "Old feed subscription".

## 3. Finish

- [x] 3.1 Update existing tests that expect out-of-region events or areas, namely `test_geo_filters.py` (Tri-State in the options and a combined filter), `test_admin_geo_filter.py`, `test_index_geo_filter.py`, `test_calendar_feeds.py` and the sitemap, discover and search tests that use New York venues, to the new behavior, and fix the roughly 40 other test files whose events have no `venue=` (archive, band pages, act index, ordering, redirect, cache, performers and others): give the shared fixtures and helpers, including `discover_fixture.py`, a New England venue, and audit every other `Event.objects.create` without a venue; check the "Venues by region" scenario against the fixture (it has no Tri-State rows); and check the "event-geo-filter" scenarios the delta rewrites (metro, region and state, no filter, unknown value, metro from another state) have passing tests.
- [x] 3.2 Run the whole suite with the network blocked and verify it passes, with every scenario in `specs/` covered.
- [ ] 3.3 Count the upcoming events hidden at out-of-region venues, and separately those with no venue (visible before, hidden now), list venues with a blank state for an editor, and note `PRODUCTION.md` with the scope rule.
