# Design

## Context

See proposal.md for the motivation.
- **How OpenDate pages are read now:** the ticketing source follows up to 10 platform event links per venue (`parse_ticketing_listing`), and `parse_ticketing_event` reads each page's JSON-LD with `parse_json_ld`.
- **Date-only starts:** for a date-only `startDate`, `to_starttime` returns midnight and `all_day=True`, and `save_event` then sets `starttime_override = "time TBA"`.
- **Event identity:** an event's `external_id` is `"json-ld:" + stable_id(url or page_url, title if no url, starttime.isoformat())`. OpenDate's JSON-LD has no `url`, so the id is built from the page URL, the title and the start time.

**What an OpenDate event page holds.** Seen on `app.opendate.io/e/emo-night-brooklyn-november-06-2026-754254`:
- **JSON-LD:** `"startDate": "2026-11-06"` and `"endDate": "2026-11-07"`, dates only.
- **The page's event data:** a `<script type="application/json" class="js-react-on-rails-component" data-component-name="AddConfirmToCalendar">` block holding `{"confirm": {"id": 754254, "start_time": "2026-11-06T22:00:00.000-05:00", "end_time_for_calendar": "2026-11-07T02:00:00.000-05:00", "title": ..., "venue": {...}}}`, with no doors time.
- **The visible text:** "Doors: 9:00 PM - Show: 10:00 PM". So `start_time` is the show time.

## Goals / Non-Goals

**Goals:**
- Real start times for OpenDate events, with no extra requests.
- No duplicates when a "time TBA" event gains its time.

**Non-Goals:**
- **Other platforms.** Prekindle, for example, also has date-only events (31 today). Each platform's page differs, so each gets its own change once its page has been looked at.
- **End times and doors times.** The event model has no field for either.

## Decisions

**1. Read the start time in a small helper, `opendate_start_time(html)`, in `parsing.py`.**
- **What it does:** it finds every `script.js-react-on-rails-component[type="application/json"]` block, parses it as JSON and returns `confirm.start_time` as an aware datetime.
- **What it returns otherwise:** `None` when there's no such block, the JSON is invalid, or `start_time` is missing or unparseable.
- **Why match on content:** it matches on the `confirm.start_time` shape rather than on `data-component-name`, because OpenDate could rename the component.
- **Alternative: read the visible "Show: 10:00 PM" text.** That breaks on any layout change, and it has no timezone. The data block is machine-readable and includes the offset.

**2. Apply the time in `parse_ticketing_event`, only for OpenDate pages, and only to an event that is all-day.**
- **Which pages:** the page's host must end with `opendate.io`.
- **When the time is used:**
  - The page must give exactly one JSON-LD event. An OpenDate event page describes a single event.
  - The event must be all-day.
  - The helper's time must fall on that event's date in Eastern time (`timezone.localdate`).
- **What happens then:** `starttime` is set to that time, and `all_day` to `False`.
- **Why the same-date check:** it protects against a block that describes a different event.
- **Why only all-day events:** a full time already in the JSON-LD always wins. So if OpenDate fixes its JSON-LD, the helper stops having any effect, and nothing needs undoing.
- **Alternative: a separate OpenDate source in the report.** That's more machinery for a single field, and the venues would have to be checked again.

**3. Keep the event's identity built from the JSON-LD date.**
- **How:** `parse_json_ld` already fixes `external_id` from the original `startDate` (midnight, for date-only values) before Decision 2 changes `starttime`.
- **Why it matters:** an event's id is the same whether or not the time was found, so a re-fetch updates the existing "time TBA" event (`save_event` looks up by `external_id`) and creates no new one.
- **What to verify:** a test checks that the id doesn't change once the time is filled in.
- **Alternative: delete and re-create the events.** That would lose admin edits and approval, and `fetch_events` only deletes stale events for iCal venues.

**4. Follow OpenDate ticket links for placeholder midnights on venue sites.**
- **When:** in `parse_json_ld` in the spider (the venue's own JSON-LD source), after parsing.
- **Placeholder midnight:**
  - **Rule:** the event isn't all-day; its start is 00:00 in Eastern local time, or 05:00 UTC; and its ticket link is an OpenDate event page (`app.opendate.io/e/...`).
  - **Why both times:** The Cut's 05:00 UTC is midnight EST, which shows as 1 am during daylight time. So matching only local midnight would miss the events before November 1.
- **How:**
  - Events that aren't placeholders are added at once, as now.
  - For each placeholder, the spider requests the OpenDate page with `cb_kwargs` carrying the event, and doesn't add the event yet.
  - The callback applies Decision 1's helper with Decision 2's same-date check. It compares against the event's date in Eastern standard time, so 05:00 UTC means the 6th, not the 5th.
  - If there's no match, it marks the event all-day ("time TBA"). Either way, it then adds the event.
  - The errback does the same as the no-match case, so a failed request never drops an event.
- **Limit:** follow-ups count against a cap of 50 per venue, the import's existing per-venue limit. Beyond that, events are saved as "time TBA". They go through the usual polite crawl settings: robots.txt, at most 2 concurrent requests per domain, and throttling.
- **Identity:** each event's `external_id` was fixed at parse time from the original value, as in Decision 3. So a re-fetch updates The Cut's 23 events and creates no duplicates.
- **Alternative: mark every venue-site midnight as "time TBA" without following links.** It's cheaper, but the times are one request away, and "time TBA" is less useful than 8 pm.
- **Alternative: make the heuristic apply to every link, not just OpenDate.** Other platforms' pages differ, and the helper only understands OpenDate. Other platforms can be added later.

## Risks / Trade-offs

- **[OpenDate changes its page]** → The helper returns `None`, and events fall back to "time TBA", which is today's behaviour. The trimmed fixture records the page as it is now.
- **[`start_time` is the show time, not the doors time]** → This matches what other sources store. Ticketmaster's `localTime`, for example, is the show time.
- **[A real midnight show with an OpenDate link]** → The link is followed and its `start_time` (midnight) is used, so the result is still correct, at the cost of one request.
- **[Repeated requests]** → Every fetch re-requests The Cut's OpenDate pages, even for events whose time is already known. That's about 25 requests per run. If this grows, skipping events already saved with a time is a later optimisation.
- **[A late show just after midnight]** → If `start_time` is 00:30 on the 7th and the JSON-LD says the 7th, the dates match and the time is used. If the JSON-LD said the 6th, the dates differ and the event stays "time TBA". That's safe, just not perfect.

## Testing

- **No network access.** Tests read a trimmed copy of the real OpenDate page from `core/tests/fixtures/`, keeping the JSON-LD script and the `AddConfirmToCalendar` block, with no keys or cookies.
- **Spider tests** feed fixture pages to `parse_ticketing_event` as built `HtmlResponse` objects, like the existing tests in `test_event_spider.py`.
- **Placeholder midnights:** these tests feed a small venue page whose JSON-LD has a 05:00 UTC start and an OpenDate offer URL. They check that `parse_json_ld` yields a request for the OpenDate page. Then they call its callback with the OpenDate fixture, and its errback with a fake failure, and check the event that gets added.
- **The "updated, not duplicated" scenario** is tested through `fetch_events`, with the spider patched as in `test_fetch_events.py`. It saves the event once without the time, then once with it.
- **External services:** OpenDate is the only one this change involves, and it is replaced by the saved page.

## Migration Plan

No migration is needed. After deploying, re-fetch the OpenDate venues, The Cut included (`fetch_events --sheet-ids ...`), to fill in the times of events already saved. Rolling back is just reverting the code; events then keep whatever times they already have.
