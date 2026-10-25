# Design

## Context

`fetch_events` reads `event_sources.csv`, which `check_event_sources` writes, and picks one source per venue. It crawls the venue sites with a Scrapy spider (`core/event_fetching/spider.py`), sends unstructured pages to Claude, and saves results through `save_event`. `save_event` takes a plain event dict (title, artists, starttime, all_day, description, hyperlink, ticket_hyperlink, price_amount, is_cancelled, external_id) and upserts on `external_id`. Venues are synced from the Google Sheet by `sync_venues_from_gsheets`, which writes only the fields mapped from sheet columns.

The relevant Discovery API facts (v2, `https://app.ticketmaster.com/discovery/v2/`):
- The key is passed as the `apikey` query parameter.
- Limits are 5,000 calls per day and 5 per second.
- Deep paging stops at the 1,000th result, so `size * page` must stay under 1000.
- `/venues.json?keyword=&stateCode=` searches venues.
- `/events.json?venueId=&startDateTime=&sort=date,asc&size=` lists a venue's events.
- Each event has `id`, `name`, `url`, `dates.start.{localDate,localTime,dateTime,timeTBA,noSpecificTime}`, `dates.status.code` (onsale, offsale, canceled, postponed or rescheduled), `priceRanges[].min`, `classifications[]` with a `primary` flag and `segment.name`, `_embedded.attractions[].name`, `info` and `pleaseNote`.

## Goals / Non-Goals

**Goals:**
- Produce event dicts in the shape `save_event` already accepts, so saving, deduplication, approval handling and reporting stay shared.
- Keep the Ticketmaster code isolated in one module that can be tested with recorded API responses.

**Non-Goals:**
- Discovering Ticketmaster venues that aren't in the sheet. A state-wide event sweep could suggest new venues later.
- Writing Ticketmaster IDs back to the Google Sheet.
- Other ticketing APIs, such as AXS, Eventbrite or DICE.
- Merging the same show found by two sources at one venue. This is avoided by giving each venue a single source, as described below.

## Decisions

**1. Store the link on `Venue` as `ticketmaster_venue_id` (CharField, null, blank, db_index).**
- **Alternatives:**
  - A sheet column. This would make the sheet the source of truth, but it means editing the shared sheet and sync code before we know the matching works.
  - A separate mapping table. That is more structure than one ID per venue needs.
- **Why the field is safe:** the sheet sync never touches unmapped fields, so a DB field survives re-syncs. It can be promoted to a sheet column later.

**2. Match venues automatically only when the match is certain, and report the rest.**
- **Depends on `add-venue-place-lookup`.** The first real dry run (2026-10-25) linked only 3 of 23 venues. The sheet's coordinates turned out to be town centres: 537 of 729 venues share theirs with another venue. You chose to keep the 1 km rule and fix the coordinates first. Matching therefore uses `Venue.exact_location`, which is the confident Google Places location when there is one.
- **How:** for each venue, search `/venues.json?keyword=<name>&stateCode=<state>`. Normalize both names: lowercase, drop "the", punctuation and words like "music hall", "club" and "theatre"/"theater", then compare. Compute the haversine distance from the venue's coordinates.
- **Link** only when exactly one candidate's normalized name matches (equal, or one contains the other) and it lies within 1 km.
- **Report everything else** with candidates for a person to decide. A wrong link would attach another venue's events, so false negatives are much cheaper than false positives.
- **Fallback search:** Crossroads Presents names (e.g. "MGM Music Hall" vs Ticketmaster's "MGM Music Hall at Fenway") are why containment counts as a match. A second search by city name is the fallback when the name search returns nothing.

**3. Call the API with `requests` and a small throttled client, not Scrapy.**
- The API returns JSON, and a linked venue normally needs one events call (`size=50` matches `MAX_EVENTS_PER_VENUE`). About 25 venues means roughly 25 calls per run.
- A synchronous client with a minimum of 0.25s between calls and retry with back-off on 429/5xx (2 retries) is simpler than adding it to the Scrapy crawl. It can run before or after the crawl in the same process.
- No new dependency: `requests` is already in `requirements.txt`.

**4. Give each venue a single source: Ticketmaster replaces ticketing and AI, but not iCal or JSON-LD.**
- Linked venues whose report source is `ticketing` or `ai-extraction`, or that are missing from usable report rows, go to the API. Venues with `ical` or `json-ld` keep it.
- **Why:**
  - A venue's own feed is often more complete. Blue Ocean Music Hall's iCal, for example, includes shows Ticketmaster doesn't sell.
  - One source per venue avoids duplicate events under two different external IDs.
- `--sheet-ids` and `--all` keep their meaning. A new `--skip-ticketmaster` flag mirrors `--skip-ai`.

**5. Map API events to the event dict as follows:**

| Field | Value |
|---|---|
| `external_id` | `tm:<id>` |
| `title` | `name` |
| `artists` | attraction names, except those whose name appears in the title (case-insensitive), joined with ", ". Real titles often add a tour name, as in "Holywatr: Deo Gratias Tour" with attractions Holywatr and Mercury, so an exact-match rule would repeat the headliner |
| `starttime` | `dates.start.dateTime` (UTC, ISO) when present; otherwise `localDate` + `localTime` made aware in `settings.TIME_ZONE` |
| `all_day` | true when `timeTBA` or `noSpecificTime` is set, or there is no time |
| `hyperlink` and `ticket_hyperlink` | `url` |
| `price_amount` | the lowest `priceRanges[].min`, or None |
| `description` | `info`, or failing that `pleaseNote`, run through `clean_description` (`save_event` escapes it) |
| `is_cancelled` | `dates.status.code == "canceled"` |

- **Time zone:** every venue in the sheet is in US Eastern time, which is `TIME_ZONE`, so local-time fallback is safe.
- **Skipped events:** those whose primary classification segment is not "Music" (including events with no classification), events flagged `test`, and postponed events with no date.

**6. Restrict the API's `source` parameter to `ticketmaster,universe,frontgate`, excluding Ticketmaster Resale (`tmr`).**
- Resale listings are not the venue's primary listing and could repeat a show under another ID.
- **Checked during implementation (task 2.4):** for Paradise Rock Club on 2026-10-25, the filtered and unfiltered responses had the same 50 events, so the filter drops no primary listings.

**7. Add `ticketmaster` to `Event.source` choices.** This is a migration that changes choices only.

## Risks / Trade-offs

- **[Wrong venue match brings in another venue's events]** → Matches must be unique and within 1 km, ambiguous cases go to a person, events land unapproved, and the admin can clear the link.
- **[Ticketmaster lists only part of a venue's calendar]** (e.g. shows ticketed elsewhere) → Venues with a working iCal or JSON-LD source keep it. For venues that switch from AI extraction, compare event counts before and after on a dry run (task 4.2).
- **[API terms require attribution or restrict caching/display]** → The project is local only. Review the Partner API Terms before any public deployment and add whatever attribution they require. Event links already point to Ticketmaster.
- **[Key leakage]** → The key is read from `.env` (git-ignored) and is never logged. Error messages show the request path without query parameters.
- **[Daily quota]** → About 25 to 30 calls per run against a 5,000-a-day limit. Matching uses one or two calls per venue. The quota is not a concern unless matching runs over every venue (700+ calls), which is still within limits.

## Testing

- **Discovery API:** tests never call the API. The client is tested by mocking `requests` responses (200, 429, 5xx). Mapping and matching are tested on recorded JSON fixtures in `core/tests/fixtures/ticketmaster/`, captured once in task 2.4, with the key stripped.
- **`fetch_events` integration:** tested with the Ticketmaster client patched. Every spec scenario needs a passing test before this change is archived.

## Migration Plan

1. Apply the migration. The new field starts empty, so behavior is unchanged.
2. Add `TICKETMASTER_API_KEY` to `.env`. It is free from developer.ticketmaster.com.
3. Run `match_ticketmaster_venues --dry-run`, review the report, run it for real, and settle ambiguous venues in the admin.
4. Run `fetch_events --sheet-ids <linked ids> --dry-run`, then for real.

To roll back, clear the links (or pass `--skip-ticketmaster`), so those venues go back to their report source. The migration can be reversed.

## Open Questions

- Do the Partner API Terms require a visible "Powered by Ticketmaster" mark or limit how long event data can be stored? This doesn't affect local use; it must be settled before going public.
