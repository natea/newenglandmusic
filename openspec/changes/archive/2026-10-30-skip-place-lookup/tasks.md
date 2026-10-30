## 1. The status

- [x] 1.1 Add `SKIPPED = "skipped", "Not looked up (no single place)"` to `Venue.PlaceLookupStatus`, with its migration. Verify that `makemigrations --check` is clean and the migration only alters the field's choices.

## 2. Lookups skip it

- [x] 2.1 Exclude `SKIPPED` venues in `lookup_venue_places`'s `selected_venues`, so every mode skips them, and say so in the command's docstring. Verify with mocked tests that a skipped venue gets no request in a plain run, with `--refresh`, `--review`, `--refresh-stale`, and when named with `--sheet-ids`, and isn't in the report.

## 3. Admin

- [x] 3.1 Add the "Don't look up on Google" action to `VenueAdmin`: clear the place fields as "Clear place lookup" does, set `SKIPPED`, and `save()` each venue. Verify with admin tests that the fields are cleared, the status is set, an event's stored HTML uses the sheet's coordinates, clearing it again blanks the status, and the status filter lists it.

## 4. Docs and check

- [x] 4.1 Document the action in PRODUCTION.md's Google Places section, for festivals and other venues with no single place. Run the whole suite with outbound network blocked. Verify that it passes.
