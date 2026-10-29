## Why

Festivals, Porchfests and other events spread across a town have no single place for Google to find. A lookup matches them to a park, a plaza or the town itself, and an admin has to clear them. Of the 84 venues still needing review on production (2026-10-29), 41 are festivals. But "Clear place lookup" only resets a venue: the daily job runs a plain lookup on every venue with no lookup status, so the next night it searches for each one again and puts most back in review. There's no way to say "this one has no place on Google; leave it".

## What Changes

- **A "don't look up" status.** A new lookup status, "Not looked up (no single place)", for venues an admin has decided have no Google place. Such a venue keeps the sheet's town coordinates, and no lookup searches for it.
- **An admin action to set it.** "Don't look up on Google" in the venue admin's actions, for the selected venues. It removes any matched place (ID, coordinates, review reasons and distance), as clearing does, and sets the new status. Its events' stored HTML is re-rendered, so their map pins move back to the town.
- **Lookups skip it.** A plain run, `--refresh`, `--review` and `--refresh-stale` all leave these venues alone, even when named with `--sheet-ids`. The run's report doesn't count them as failures or reviews.
- **Reversible.** "Clear place lookup" on such a venue resets it, so the next run searches for it again.
- **Filterable.** The existing lookup-status filter in the venue admin gains the new status, so an admin can see and undo them.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `venue-place-lookup`: an admin can mark a venue as not to be looked up, and every lookup skips it.

## Impact

- **Code:**
  - `Venue.PlaceLookupStatus` gains `SKIPPED`, with a migration (the field's choices only; the column fits it);
  - `lookup_venue_places` excludes skipped venues in every mode;
  - the venue admin's new action.
- **Data:** none changes on deploy. Admins choose the venues; nothing is marked automatically.
- **Cost:** saves Places searches: about 40 festivals no longer searched for each time they're cleared.
- **No change for visitors,** beyond those venues' pins staying at the town centre.
