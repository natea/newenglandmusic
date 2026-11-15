Issue: [#14 Create an Export to CSV/Excel option for the venue database](https://github.com/natea/newenglandmusic/issues/14)

# Proposal

## Why

The venue database is only browsable one record at a time in the admin. Editors and admins who want to sort, filter or count venues, for example how many open-booking venues each state has, have no way to get the data out. Issue 14 asks for a straightforward export of the venue list, with everything the site holds about each venue, to a spreadsheet format for quick analysis. The thread settled that it is for the site's editors and admins only.

## What Changes

- **An "Export to CSV" button on the venue list in the admin.** It downloads a CSV file, with one row per venue, of the venues the list is currently showing. With no search or filter that's every venue. With a filter or search applied it's only the matching ones, so an editor can export "active venues in MA".
- **All the details the site holds about a venue**, as columns: the sheet's fields, the neighborhood, the event-source links and the saved result of the last event-source check.
- **Left out because of Google's terms:** the Google place coordinates and the distance worked out from them, which the site may keep for only 30 days and not hand out. The Google place ID, which the site may keep, is included, as is the lookup status. The sheet's own coordinates are included.
- **Only for signed-in staff who may view venues.** Anyone else is refused, with no data sent.
- **Opens cleanly in Excel and Sheets**, and a cell can't run as a formula when the file is opened.
- A public export for visitors is not built. It is noted as a possible later addition.

## Capabilities

### New Capabilities

- `venue-export`: downloading the venue list from the admin as a CSV file, who may do it, and which data is included or left out.

### Modified Capabilities

None. No existing spec describes the venue list in the admin.

## Impact

- **Admin:** `VenueAdmin` gains one route and a button on its list page, with a small list template for it. Nothing else in the admin changes.
- **Code:** a small module that turns venues into CSV rows.
- **No model, migration, command or external service changes.** Nothing is written, and no outside service is called.
- **Docs:** a short note in `PRODUCTION.md` or the admin docs on what the file holds, if one fits.
