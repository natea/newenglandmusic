Issue: [#28 Add CSV export button to the artists and bands roster/listing](https://github.com/natea/newenglandmusic/issues/28)

## 1. Export module

- [ ] 1.1 Add `core/act_export.py` with the hand-listed columns, `NOT_EXPORTED`, the members and bands cells, and `act_row()`, reusing `cell()` from `core/venue_export.py`; verify with tests for the row fields, band members, an artist's bands, blank values and the credit-bound data being absent.
- [ ] 1.2 Add the field-coverage test for `Artist` and `Band`; verify it fails when a field is neither exported nor named in `NOT_EXPORTED`.
- [ ] 1.3 Write the automated tests for the "Credit-bound and bookkeeping data is left out" and "Cells can't run as formulas" scenarios (formula-like note, commas and line breaks).

## 2. The button and download

- [ ] 2.1 Add the export route, view and `can_export` context to `MusicActAdmin`, sharing the streaming code with `VenueAdmin` without changing its behaviour; verify the existing venue export tests still pass.
- [ ] 2.2 Add the Artist and Band change-list templates showing the button only when `can_export`; verify the button is present for permitted staff and absent otherwise.
- [ ] 2.3 Write the automated tests for every scenario of "Staff can download the artist and band lists as CSV": everything, filtered, searched, more than a page, held acts, the byte order mark and filenames.
- [ ] 2.4 Write the automated tests for "Only staff who may view that kind of act can export": signed out, staff without permission (artists versus bands), and the admin group.

## 3. Finish

- [ ] 3.1 Run the whole suite with the network blocked and verify it passes, with every scenario in `specs/act-export/spec.md` covered.
- [ ] 3.2 Mention the new buttons in `PRODUCTION.md` if it describes the venue export, and verify it matches the shipped behaviour.
