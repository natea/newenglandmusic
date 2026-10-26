## Why

On 2026-10-26, 167 upcoming shows on Render had two or more copies, at the same venue and start time with the same title, and 101 of them appeared twice on the public site. The import matches events only on their source's ID, so the same show arriving under a new ID becomes a second event:
- **97 shows:** an Eventbrite API copy, plus the copy scraped earlier from the venue's Eventbrite page under a JSON-LD ID.
- **38 shows:** AI extraction gave the same event a new ID on a later run, because its ID depends on the link the model returned.
- **19 shows:** a venue's iCal feed and then its JSON-LD, after its saved source changed.

## What Changes

- **The import adopts an existing copy instead of creating a duplicate.** When an event's ID is new, but its venue already has an imported event at the same start time with the same title (ignoring case, spaces and punctuation), that event is updated and takes the new ID. Its approval stays, and so does its kind, unless the import's kind is new information. Events entered by hand are never adopted.
- **A one-off cleanup command, `dedupe_events`,** merges the duplicates already saved:
  - It keeps the copy the daily fetch still updates (the one from the venue's latest fetch source), or else the oldest.
  - The kept copy is approved if any copy was, and takes a kind an admin set on any copy.
  - The other copies are deleted. `--dry-run` lists what it would do and changes nothing.
  - Only upcoming imported events are considered.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `event-import`: "Imported events are queued for review without duplicates" also matches on venue, start time and title, and a new requirement covers the cleanup command.

## Impact

- **Code:** `fetch_events.save_event`, and a new `dedupe_events` command, recorded as a job run.
- **Tests:** scenarios for adopting each kind of duplicate, for hand-entered events, and for the cleanup's choices. No network.
- **Data:** the cleanup deletes rows on Render, and is run only after the user has checked its dry-run list.
