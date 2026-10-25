# Design

## Context

See proposal.md. The sheet has one row per venue in the "V3 - Flattened" tab. Other tabs hold reference data; the "New Booking Types" tab supplied the `BookingType` choices. The sheet is shared and edited by hand, so names, yes/no values and sizes are inconsistent: "Y", "Maybe?", "???", and "Small (<100)".

## Goals / Non-Goals

**Goals:**
- Mirror the sheet into the database repeatably, without duplicates, so venues can be filtered and linked to events.

**Non-Goals:**
- Writing back to the sheet.
- Syncing from the original sheet. Only the copy with `Venue_ID` is used.
- Cleaning up duplicate rows or closed venues. Duplicates keep separate IDs, and cleanup is left to the people editing the sheet.

## Decisions

**1. Add a stable `Venue_ID` key column (`sheet_id` in the model, unique).**
- **Alternatives:**
  - Match on name: the old approach, which breaks on 16 duplicate rows and on renames.
  - Match on row number: this breaks when rows are sorted or inserted.
- An explicit ID survives both.

**2. Read the sheet with the `gog` CLI instead of a Google API client in Django.**
- `gog` is already authorized on the machine and avoids storing OAuth credentials in the app.
- **Trade-off:** the sync depends on an external binary. It fails with a clear error when `gog` is missing or fails.
- The Sheets API drops trailing empty cells, so rows are padded out to the header length.

**3. Never delete venues.**
- Events reference venues, and a mistaken edit in the sheet must not cascade into lost events.
- Venues missing from the sheet are reported instead.

**4. Run the sync in a single transaction.**
- Any validation error, such as a duplicate ID, leaves the database untouched.
- `--dry-run` reuses the same path and rolls back at the end, so it reports exactly what a real run would do.

**5. Use unknown (null) for yes/no values the sheet doesn't answer.**
- Values like "Maybe?" and blanks are stored as null, not false, so filters such as "LGBTQ+ friendly" don't treat unknown as no.
- `is_active` follows the same rule. Only an explicit "N" hides a venue.

## Risks / Trade-offs

- **[Sheet column renamed]** → The sync raises a `KeyError` on the missing column instead of silently writing blanks. A clearer error message is a possible improvement.
- **[Venue_ID edited by hand]** → The sync would treat the row as a new venue and report the old one as missing. The command's docstring states that IDs must never change.
- **[No automated tests yet]** → The sync was verified by hand against the live sheet: 729 venues created, then a re-run updated 729 and created 0. tasks.md adds the tests this change still needs before it can be archived.

## Testing

- **Google Sheets:** tests never call `gog`. They mock `get_rows_from_google_sheets` with in-memory header and rows.
- **The `gog` error paths:** these are tested by mocking `subprocess.run`.
