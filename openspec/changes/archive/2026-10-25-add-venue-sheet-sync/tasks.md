# Tasks

> Tasks 1.1–3.2 were built before this spec was written. Tests 2.4–3.5 were added afterwards: 29 tests in `core/tests/test_venue_model.py`, `test_venue_pickers.py` and `test_sync_venues_from_gsheets.py`. Before archiving, two deliberate breaks (letting inactive venues through the pickers, and parsing a blank as "no") were each caught by the tests, and the full suite passed: 62 tests.

## 1. Sheet preparation

- [x] 1.1 Copy the original sheet to "Northeastern US Music Venues - v3 (venue-db copy)" and add a `Venue_ID` column (AA) with V0001–V0729; verified 729 unique IDs in the copy

## 2. Venue model, admin and pickers

- [x] 2.1 Rebuild `Venue` around the sheet's columns with `Size` and `BookingType` choices, `location` and `google_maps_link` properties, and migration 0075 (commit `f148d7f`); verified that migrations apply
- [x] 2.2 Update `VenueAdmin` with filters and fieldsets for the new fields (commit `f148d7f`); verified in the admin
- [x] 2.3 Exclude inactive venues from venue autocomplete and the submission form, and label them with their location (commit `f148d7f`); verified in the submission form
- [x] 2.4 Add `core/tests/test_venue_model.py` covering `location` and `google_maps_link` (with and without coordinates); verify with `python manage.py test core.tests.test_venue_model`
- [x] 2.5 Add tests that venue autocomplete and the submission form leave out `is_active=False` venues, keep `is_active=None` venues, and label results "Name (City, ST)"; this covers "Searching for a closed venue". Verify that the tests pass

## 3. Sync command

- [x] 3.1 Remove `import_venues_from_gsheets`, `load_coordinates_from_google_maps` and `core/utils_maps.py` (commit `f148d7f`; the earlier upsert fix is commit `281269d`); verified there are no remaining imports
- [x] 3.2 Add `sync_venues_from_gsheets` with Venue_ID matching, value parsing, warnings, no deletes, a single transaction and `--dry-run` (commit `f148d7f`); verified that a live sync created 729 venues and a re-run created none
- [x] 3.3 Add `core/tests/test_sync_venues_from_gsheets.py` with unit tests for `parse_yes_no` ("Y", "yes", "N", "Maybe?", blank), `parse_size`, `parse_genres` ("Funk; Jazz;", "ALL") and the booking-type mapping; verify that they pass
- [x] 3.4 In the same file, test the command end to end with `get_rows_from_google_sheets` mocked to return header + rows (no `gog` call). Cover: new row, edited row, same-name rows with different IDs, missing Venue_ID column, duplicate Venue_ID (nothing saved), row without an ID (skipped with a warning), row removed from the sheet (venue kept and reported), unknown booking type (warning), `--dry-run` (nothing saved, counts reported), and a field not in the sheet being preserved. Verify that each spec scenario maps to a passing test
- [x] 3.5 Test that the `gog` call fails cleanly: `FileNotFoundError` and `CalledProcessError` from `subprocess.run` each raise a `CommandError` with a clear message, and short rows are padded to the header length. Verify that the tests pass

## 4. Integration

- [x] 4.1 Run the full test suite (`python manage.py test`) and verify that it passes; then archive with `openspec archive add-venue-sheet-sync`
