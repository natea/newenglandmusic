# Proposal

## Why

OpenDate event pages (`app.opendate.io/e/...`) give only a date in their JSON-LD, for example `"startDate": "2026-11-06"`, so every event we import from them shows "time TBA". The same page also stores the full start time in a data block its "add to calendar" button uses: `"start_time": "2026-11-06T22:00:00.000-05:00"`. Eleven venues in the source report sell tickets through OpenDate, Alchemy (V0657) among them, so all of them lose their show times today.

Some venues' own sites show OpenDate's events on their own event pages and give the same date-only start as a placeholder midnight. The Cut (V0181, thecutlive.com) gives every show `05:00 UTC`, which is midnight Eastern standard time. So 23 of its 27 upcoming events show "12am" or "1am". Each of those events links to its OpenDate page, which has the real time.

## What Changes

- **OpenDate start time:** when the import reads an OpenDate event page, it takes the start time from that data block (`start_time`, the show time with its timezone offset) instead of the date-only JSON-LD value.
- **Fallback:** the date-only value stays the fallback. If the block is missing, can't be read, or gives a different date from the JSON-LD, the event keeps its date and shows "time TBA", as it does now.
- **Placeholder midnights on venue sites:** when a venue's own JSON-LD gives an event a start at exactly midnight Eastern (00:00 local, or 05:00 UTC) and the event's ticket link is an OpenDate event page, the import follows that link and takes the start time from it. If the link gives no usable time, the event is saved as "time TBA", not as midnight.
- **Stable identity:** an event keeps the same identity when its time is filled in. That way the 9 Alchemy events already saved as "time TBA" are updated in place, not duplicated.
- **Spec catch-up:** the JSON-LD requirement now states what the parser already does since the fix in `097fe24`: a date-only `startDate` makes the event all-day, shown as "time TBA". The spec only said this for iCal.
- **Doors times are out of scope.** OpenDate's data block has no doors time (only `id`, `title`, `start_time`, `end_time_for_calendar` and `venue`), and the event model has no field for one.
- **Reporting the bug to OpenDate** (asking them to include the time in their JSON-LD) is a separate step for the user. This change doesn't depend on it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `event-import`:
  - the JSON-LD requirement adds the date-only rule
  - the ticketing-page requirement adds reading OpenDate's start time from the page's data block
  - a new requirement covers placeholder midnights on venue sites that link to OpenDate

## Impact

- **Code:**
  - `core/event_fetching/parsing.py`: a helper that reads OpenDate's start time from a page.
  - `core/event_fetching/spider.py`:
    - `parse_ticketing_event` applies that helper to OpenDate pages.
    - `parse_json_ld` follows OpenDate ticket links for placeholder midnights.
- **Tests:** `core/tests/test_event_parsing.py` and `core/tests/test_event_spider.py`, using a trimmed copy of a real OpenDate page saved as a fixture.
- **Data:**
  - **Alchemy:** re-fetching V0657 fills in the times of its 9 upcoming events.
  - **Other OpenDate venues:** their events gain times on their next fetch. The 10 others in the report are V0076, V0181, V0201, V0222, V0253, V0254, V0602, V0632, V0671 and V0724.
  - **Venues whose own site uses JSON-LD:**
    - **The Cut** (V0181): its 23 placeholder-midnight events gain real times. Each fetch also requests up to one OpenDate page per such event (about 25 today).
    - **Zenbarn** (V0724): it's also a JSON-LD source with OpenDate links. It's affected only if its site uses the same placeholder midnights.
- **APIs and dependencies:** none.
- **Requests:** OpenDate ticketing pages need no new requests, because the data block is on the page the crawler already fetches. Placeholder midnights on venue sites add one OpenDate page request per affected event, under the usual crawl limits.
