Issue: [#28 Add CSV export button to the artists and bands roster/listing](https://github.com/natea/newenglandmusic/issues/28)

# Proposal

## Why

Sooz asked (issue 28) for an "Export to CSV" button on the artists and bands lists, like the one on the venue list. Editors review acts in the admin and want to analyse them in a spreadsheet, as they already can with venues (`venue-export`).

## What Changes

- The admin's Artist list and Band list each get an "Export to CSV" button, working as the venue list's does: it downloads the acts the list is showing (its search, filters and order, every page).
- A new export module lists the columns of an act row by hand, with a test that fails when a new act field is neither exported nor named as left out.
- Fields whose licence needs credit or that are bookkeeping are left out (see the design); the file holds what the site may share.
- Only signed-in staff who may view that kind of act see the button or get the file.
- Cells that could run as formulas are neutralised, as in the venue export.

## Capabilities

### New Capabilities
- `act-export`: downloading the admin's artist and band lists as CSV files.

### Modified Capabilities

(none)

## Impact

- `core/admin.py` (`MusicActAdmin`: export URL, view, list context), a new `core/act_export.py`, and change-list templates for Artist and Band.
- No model, migration or outside-service change. Reuses the formula guard and cell formatting from `core/venue_export.py`.
- Tests in `core/tests/`, none touching the network.
