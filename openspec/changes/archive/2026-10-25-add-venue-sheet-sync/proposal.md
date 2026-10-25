# Proposal

> Retroactive: this documents behavior already built in commits `281269d` (`fix-venue-upsert`) and `f148d7f` (`venue-db`), so later changes have a baseline spec. Automated tests were added before it was archived.

## Why

The venue database is maintained in the "Northeastern US Music Venues - v3" Google Sheet: 729 venues with 26 columns covering location, size, genres, booking and accessibility. The inherited nycnoise `Venue` model and its `import_venues_from_gsheets` command assumed a different, NYC-specific sheet. Its upsert crashed, and it matched venues by name, which breaks for the 16 rows that share a name, city and state. The site needs a reliable, repeatable way to make the database mirror the sheet.

## What Changes

- **Rebuild `Venue` around the sheet's columns:**
  - location: name, state, city/town, county, coordinates
  - activity: active flag
  - style: venue type, size, genres and notes
  - booking: open booking, booking type, open mic, website, booking URL and notes
  - access: age policy, accessibility notes, family/LGBTQ+/diverse flags, safety flag/URL/notes
  - derived: `location` ("City, ST") and a Google Maps link
- **Give each venue a stable key.** A `Venue_ID` column (V0001–V0729) was added to a working copy of the sheet. The original sheet is left untouched.
- **Add `sync_venues_from_gsheets`.** It reads the sheet with the `gog` CLI and upserts venues by `Venue_ID`. It never deletes, warns about rows it can't use, and supports `--dry-run`.
- **BREAKING:** removed `import_venues_from_gsheets`, `load_coordinates_from_google_maps` and `core/utils_maps.py`, along with the NYC-specific venue fields they used.
- **Update venue search and event submission** to skip inactive venues and to label venues with their location.

## Capabilities

### New Capabilities

- `venue-sheet-sync`: keeps the venue table in step with the Google Sheet, matching rows by `Venue_ID`.

### Modified Capabilities

None. There were no specs before this change.

## Impact

- **Model:** `core/models.py` (`Venue`), with migration 0075.
- **Admin and views:** `core/admin.py`, `core/views/autocomplete.py`, `core/views/event_submission.py` and venue templates.
- **New command:** `core/management/commands/sync_venues_from_gsheets.py`.
- **External:** this depends on the `gog` CLI, authorized for Sheets, and on the copied sheet `1QBzKHOUWOR0Fw0ODrwEep5eGfZg4SmTUq4PsaCbbnGQ` (tab "V3 - Flattened").
