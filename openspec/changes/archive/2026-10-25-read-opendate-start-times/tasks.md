# Tasks

## 1. Date-only JSON-LD (spec catch-up)

- [x] 1.1 Add a test to `test_event_parsing.py` for the "Date-only start" scenario: a node with `startDate` "2026-11-06" is parsed as all-day on November 6. Also extend `test_fetch_events.py` to check that such an event is saved with `starttime_override` "time TBA". Verify that the tests pass; this behaviour already exists since `097fe24`, so no code change should be needed.

## 2. OpenDate start times

- [x] 2.1 Save a trimmed copy of a real OpenDate event page as `core/tests/fixtures/opendate_event.html`, keeping its JSON-LD script and its `AddConfirmToCalendar` data block and nothing private. Verify the file has no cookies, tokens or keys.
- [x] 2.2 Add `opendate_start_time(html)` to `core/event_fetching/parsing.py` (design decision 1). Add tests to `test_event_parsing.py`: it returns 10:00 pm Eastern on November 6 for the fixture, and `None` for a page with no block, invalid JSON, or no `start_time`. Verify that the tests pass.
- [x] 2.3 In `parse_ticketing_event` in `spider.py`, apply the time to the page's single all-day event on OpenDate pages when the dates match (design decision 2). Add tests to `test_event_spider.py`, using the fixture and edited copies of it, for these scenarios:
  - "OpenDate page with a start time": the event is no longer all-day and starts at 10 pm.
  - "OpenDate page without usable event data": no block, invalid JSON, or a different date each leave the event all-day.
  - A full time in the JSON-LD is kept.
  - A non-OpenDate page is unchanged.

  Verify that the tests pass.
- [x] 2.4 Test the "Time filled in on a re-fetch" scenario in `test_fetch_events.py`:
  - Save a fixture event once as all-day, then again with the time.
  - Check there's still one event, now with the time and no "time TBA".
  - Check that `external_id` didn't change.

  Verify that the tests pass.

## 3. Placeholder midnights on venue sites

- [x] 3.1 Add a placeholder-midnight check (design decision 4), and test it in `test_event_parsing.py`. These are placeholders: 05:00 UTC and 00:00 Eastern, each with an OpenDate ticket link. These aren't: 20:00 with an OpenDate link, 05:00 UTC with a non-OpenDate link, and an all-day event. Verify that the tests pass.
- [x] 3.2 In the spider's `parse_json_ld`, request each placeholder event's OpenDate page and add the event from the callback or errback (design decision 4). Add tests to `test_event_spider.py` for these scenarios:
  - "Venue site with an OpenDate ticket link": a request is yielded, and the callback adds the event at 8 pm. Also check that the event's `external_id` is the same with or without the time ("Placeholder time filled in on a re-fetch").
  - "OpenDate link without a usable time": the callback without a block, and the errback, both add the event as all-day.
  - "Placeholder midnight without an OpenDate link" and "Real time on a venue site": the events are added at once, with no request.
  - The per-venue cap of 50 holds.

  Verify that the tests pass.

## 4. Verify

- [x] 4.1 Run the full test suite with outbound network blocked, and verify that it passes.
- [x] 4.2 With the user's go-ahead, re-fetch Alchemy and The Cut (`fetch_events --sheet-ids V0657,V0181`), logging to `logs/fetch_events-<date>.log`. Check the results and record them here:
  - Alchemy: its events show times, for example Emo Night Brooklyn at 10 pm on November 6.
  - The Cut: its events no longer show 12am or 1am, for example Roomful of Blues on November 6.
  - Neither venue's event count grew.
  - Result (2026-10-25 17:21, `logs/fetch_events-2026-10-25.log`; labelling 888 input / 40 output Haiku tokens):
    - **Alchemy:** 10 updated, none created, still 10 events. None are "time TBA" or 12am any more. Emo Night Brooklyn is at 10:00 pm on November 6.
    - **The Cut:** 27 updated, 1 created. The new one is a new listing ("Alexandra Grace Music Studio's Songs & Spells - Late Show"), not a duplicate, and no title appears twice. Roomful of Blues is at 8:00 pm on November 6, and 21 shows are at 8 pm.
    - **Left as expected:**
      - "Battle of The Bands - Gloucester Alumni" shows "time TBA", because its OpenDate page returned an error, which was reported.
      - "Karaoke with DJ Lou" and "Live Band Karaoke with Groove Therapy" stay at 12am. Their ticket links are The Cut's own pages, not OpenDate ("Placeholder midnight without an OpenDate link"). Both are labelled karaoke, so they're hidden from review anyway.

## Workflow follow-up

- Re-fetch the other OpenDate venues (V0076, V0201, V0222, V0253, V0254, V0602, V0632, V0671) on the next scheduled run.
- Archive after review, once every scenario has a passing test.
