## 1. Stop new duplicates

- [x] 1.1 In `fetch_events.save_event`, on an external-ID miss, adopt an existing imported event at the same venue, start time and normalised title (not one saved earlier in the run, never a hand-entered one), keeping its approval and kind. Verify: tests for "Same show under a new ID", "Hand-entered event", and the existing re-run scenarios.

## 2. Merge existing duplicates

- [x] 2.1 Add `dedupe_events` (`--dry-run`), recorded as a job run, choosing and merging copies as specified. Verify: tests for "Eventbrite and scraped copies", "Equal copies", "Admin label carried over" and "Dry run".
- [x] 2.2 Run the full suite with outbound network blocked, release, then run `dedupe_events --dry-run` on Render and give the user the list. Run it for real only with their go-ahead, then check no duplicate groups remain. (2026-10-26: 167 copies of 166 shows deleted on Render after the user checked the list; none remain.)
