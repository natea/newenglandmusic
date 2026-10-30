## Context

`Venue.place_lookup_status` is a `CharField(max_length=16)` with the choices `confident`, `review` and `not_found`, and blank for "never looked up". In `lookup_venue_places`, a plain run selects active venues with a blank status; `--refresh` selects every active venue (or those named in `--sheet-ids`, active or not); `--review` selects `review`; `--refresh-stale` selects venues with a place ID older than its cutoff. The admin's "Clear place lookup" blanks the status and the place fields, and saves each venue with `save()`, which re-renders its events' stored HTML. `bin/daily.sh` runs a plain lookup and then `--refresh-stale`.

## Goals / Non-Goals

**Goals:** let an admin settle a venue with no single place once, so lookups stop searching for it and stop putting it in review.

**Non-Goals:**
- Marking festivals automatically, by name or by Google's type. Names like "Porchfest" are a good hint, but the admin decides; the "not a venue" reason already points them out.
- An admin-entered location for such venues. They keep the sheet's town coordinates.

## Decisions

**1. A status, not a separate flag.** Add `SKIPPED = "skipped", "Not looked up (no single place)"` to `PlaceLookupStatus`. The plain run's `place_lookup_status=""` filter already leaves it out, `--review` already selects only `review`, and the existing status filter shows it with no new code. A separate boolean would need its own filter and could contradict the status (a "skipped" venue that's also "confident"). Alternative rejected: reusing `not_found`, which a `--refresh` run searches again and which means something else ("Google had nothing").

**2. Excluded in `selected_venues`.** `selected_venues` is shared by every mode, so excluding `SKIPPED` there covers a plain run, `--refresh`, `--review`, `--refresh-stale` and `--sheet-ids` in one place. To look one up again, an admin clears it first; there's no override flag, keeping the command's options as they are.

**3. The action clears, then marks.** "Don't look up on Google" sets the same empty place fields as "Clear place lookup" (sharing the `CLEARED_LOOKUP` values), plus the new status, and uses `save()` so the events' pins move back to the town. Clearing such a venue blanks its status as for any other, which is the undo.

**How it's tested.** Admin tests for the action (fields cleared, status set, an event's stored HTML using the sheet's coordinates), for undoing it, and for the filter; command tests with the Places client mocked, asserting no request is made for a skipped venue in each mode and with `--sheet-ids`. Nothing reaches the network.

## Risks / Trade-offs

- **[A real venue marked by mistake never gets an exact location]** → It's listed under its own status in the filter, and one "Clear place lookup" undoes it.
- **[The migration]** → Only the field's choices change, so it alters no column and needs no data step.

## Migration Plan

Deploy (the build runs the migration). Then, in the production admin, filter the review list to festivals and choose "Don't look up on Google". Festivals already cleared tonight will be back in review after the daily run, and can be marked the same way.
