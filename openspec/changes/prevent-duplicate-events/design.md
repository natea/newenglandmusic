## Context

- `save_event` looks an event up by `external_id`; a miss creates a new, unapproved event.
- External IDs come from the source: `eventbrite:<id>`, `tm:<id>`, the iCal UID hash, a JSON-LD hash, or, for AI extraction, a hash of the link (or title) and start time. Scraped Eventbrite pages were saved as `json-ld:` IDs with the `ticketing` source.
- A venue's fetch status (`VenueFetchStatus.source`) records which source its latest fetch used.
- Labels: an event is labelled once; later fetches keep its kind, and an admin's kind always wins (`kind_set_by`).

## Goals / Non-Goals

**Goals:** no new duplicates from a changed ID; the existing ones merged without losing an approval or an admin's label.

**Non-Goals:**
- Fuzzy matching of titles or times. Two copies must share the venue, the exact start time and the normalised title. Near-misses stay separate.
- Merging hand-entered events with imported ones.
- Cleaning past events.

## Decisions

**Match key:** venue, exact start time, and the title lowercased with everything but letters and digits removed. This found every duplicate in the 2026-10-26 survey, and two different shows at one venue rarely share both a start time and a title.

**Adopting a copy in `save_event`:** on an ID miss, the venue's imported events at that start time are fetched and compared by title in Python. The first match, oldest first, is updated and given the new `external_id` and `source`. A copy already saved earlier in the same run isn't adopted, so two events with the same title and time in one feed can't overwrite each other. When the adopted event already has a kind, it keeps it, so a relabel can't flip it.

**Cleanup choice:** among a group's copies, those whose source is the venue's latest fetch source are preferred, because the daily fetch keeps them current. The oldest preferred copy is kept, or the oldest copy if none is preferred. It's approved if any copy was. If it has no admin label and another copy does, it takes the most recent admin label. The rest are deleted.

**The cleanup is a command, not a migration,** so it can be run, and dry-run, against whichever database, and it's recorded as a job run with its full list.

## Risks / Trade-offs

- [Two genuinely different events share a venue, start time and title.] → Rare, and the result is one event instead of two; the cleanup's dry run is checked by a person first.
- [An admin edited the deleted copy's title or description.] → Only approval and kind are carried over. The dry run lists both copies so such cases can be spotted.

## Migration Plan

Release, then run `dedupe_events --dry-run` on Render, show the user the list, and run it for real only with their go-ahead.
