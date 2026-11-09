Issue: [#14 Create an Export to CSV/Excel option for the venue database](https://github.com/natea/newenglandmusic/issues/14)

# Tasks

## 1. Row building

- [x] 1.1 Add `core/venue_export.py` with the explicit column list, the header, a row for one venue (yes/no/blank flags, `; `-joined genres, event-source columns from `VenueEventSource`), the formula guard, and no Google coordinate, distance or fetch time. Verify: unit tests for the "Sheet fields in the row", "Unknown flag", "Event source included", "Confident match", "Formula-like note" and "Commas and line breaks" scenarios.
- [x] 1.2 Add a test that fails when a `Venue` field is neither exported nor on a named exclusion list, so new fields need a decision. Verify: the test passes now, and fails when a field is temporarily added.

## 2. Export view

- [x] 2.1 Add the `export-csv/` route to `VenueAdmin`, wrapped in `admin_view`, that rebuilds the list's own queryset (search, filters, ordering, no pagination), checks `has_view_permission` (403 otherwise) and returns a UTF-8 CSV with a byte order mark and a dated filename. Verify: tests for the "Export everything", "Export a filtered list", "Export a searched list", "More venues than a page", "Opens in Excel", "Signed-out visitor", "Staff without permission" and "Member of the admin group" scenarios.

## 3. Button

- [ ] 3.1 Add `admin/core/venue/change_list.html`, extending the core change list, with an "Export to CSV" button that keeps the current query string and shows only when the user has view permission. Verify: a test that the button is on the list for an admin and keeps a filter's query string, and that the list of a user without permission, if they can reach it, has no button. Check at localhost:8001/admin/core/venue/ that the button sits in the toolbar and downloads a file that opens in a spreadsheet.

## 4. Docs

- [x] 4.1 Note in the admin docs what the file holds and what is left out and why. Verify: the note matches the spec's column list.
