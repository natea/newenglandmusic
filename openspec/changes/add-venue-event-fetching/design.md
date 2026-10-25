# Design

## Context

See proposal.md. Venues come from `venue-sheet-sync`. Sites range from WordPress sites with Events Calendar feeds, to Squarespace and Wix pages rendered in the browser, to Facebook-only bars. The inherited nycnoise event model already had approval (`is_approved`), price buckets and an approved-only default manager (`Event.objects`). Imported events are therefore handled through `Event.all_objects`.

## Goals / Non-Goals

**Goals:**
- Get as many venues' upcoming events as possible, from the most reliable source each one has, cheaply and politely.
- Keep a person in the loop: nothing is published without approval.

**Non-Goals:**
- Running JavaScript, for example with Playwright. About 200 venues need it, and this is a separate change.
- Ticketing-platform APIs (see `add-ticketmaster-discovery-api`).
- Fixing sites that publish wrong times, such as Black Eyed Sally's and The Main Pub.
- Paging through iCal feeds beyond their first page.
- Scheduling the import.

## Decisions

**1. Split the work into two steps, detection (`check_event_sources` → CSV) then import (`fetch_events`).**
- Detection is slow, and its output is worth reviewing by hand. Import re-runs often.
- The CSV makes the source choice visible and editable, and lets the import be scoped, as in a pilot.
- **Alternative:** detect at import time. That repeats the work and hides the decision.

**2. Pick sources in the order iCal > JSON-LD > ticketing > AI, with one source per venue.**
- Structured sources are exact and free. AI costs money and can misread pages.
- One source per venue avoids duplicate events under different external IDs.

**3. Use `requests` + BeautifulSoup for detection and Scrapy for import.**
- Detection makes a few requests per venue in a thread pool.
- Import benefits from Scrapy's robots.txt middleware, per-domain throttling (AutoThrottle, 2 concurrent requests per domain, 0.5s delay), retries, and following ticketing links.
- The Scrapy spider only collects results. All database writes happen after the crawl, because Django's ORM can't be used from Scrapy's async reactor.

**4. Parse into plain event dicts with a single save path.**
- Every source produces the same dict shape (see `core/event_fetching/parsing.py`). `save_event` is the only code that writes events. Upserting, approval keeping, escaping and price bucketing are therefore implemented once.

**5. Build external IDs as `<source>:<hash of url/uid + start time>`.**
- Recurring events often share a UID or URL, so the start time is part of the ID.
- **Trade-off:** a rescheduled event from iCal, JSON-LD or AI becomes a new event, and the old one stays. Ticketmaster IDs won't have this problem.

**6. Use Claude Haiku 5.5 for AI extraction, with a JSON-schema structured output and low effort.**
- On the pilot pages, Haiku found the same 40 events as Opus for $0.0074 against $0.2425. Sonnet added nothing.
- Structured output removes the need to parse free text.
- Pages run in 8 parallel workers.
- Page text is capped below the token count where Haiku's pricing steps up.

**7. Fall back when a source fails:**
- A malformed iCal feed goes to AI extraction of the events page.
- A 404 or 410 on the sheet's URL goes to the homepage.
- The report records the URL that actually loaded, so the import doesn't re-fetch a dead URL.

## Risks / Trade-offs

- **[Rate limiting from repeated runs]** → bot-blocked venues rose from 21 to 40 between runs. Run detection rarely, and keep the import throttled.
- **[AI misreads a page]** → Every event lands unapproved, the prompt forbids guessing, and output is validated (dates, placeholders).
- **[Sites change and the CSV goes stale]** → Re-run detection periodically. The import reports failures per venue.
- **[No automated tests for most of this]** → Only the calendar-link tests exist (commit `7260193`). The behavior was verified by pilot and full runs: 1,757 upcoming events from 154 venues. tasks.md adds the tests this change still needs before it can be archived.

## Testing

- **Venue websites:** tests never make network requests.
  - Detection functions are tested on HTML fixtures.
  - `check_venue_unsafe` is tested with a mocked `requests.Session`, including responses for robots.txt, 404, 403 and DNS failure.
  - The spider's callbacks are tested with `scrapy.http.HtmlResponse`/`TextResponse` objects built from fixtures, without starting a crawl.
- **Anthropic:** tests mock the client's `beta.messages.create` with canned responses (normal, empty, early stop, invalid JSON). No API key is needed.
- **The `fetch_events` command:** tested with `CrawlerProcess` patched to fill the results list from fixtures, so the save and report path runs against the test database.
