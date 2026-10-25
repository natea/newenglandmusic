# Tasks

> The tasks marked [x] were built before this spec was written. The change is not complete until the test tasks are done, because every spec scenario needs a passing automated test.

## 1. Event model

- [x] 1.1 Add `Event.source`, `source_url` and unique `external_id`, in migration 0076 (commit `8535366`); verified that migrations apply

## 2. Event-source detection

- [x] 2.1 Add `check_event_sources` with source preference, failure classifications, robots.txt checks, js_heavy flag and the CSV report (commit `780440d`); verified on a full run over the active venues
- [x] 2.2 Improve events-page picking: navigation-text scoring, skipping private/rental and single-event links, falling back to the homepage (commit `8ddf115`); verified on venues that had been mis-picked
- [x] 2.3 Fall back to the homepage on a 404 and record the URL that actually loaded (commit `001bd3f`); verified on Cafe Nine
- [ ] 2.4 Add `core/tests/test_check_event_sources.py` with HTML-fixture unit tests for `find_events_page_url` (nav calendar link, private events, single-event links only, file links), `looks_like_single_event_page`, `find_ical_urls` (.ics, webcal:, ?ical=), `count_json_ld_events` (nested and invalid blocks), `find_platforms`, `is_social` and `normalize_url`; verify that they pass
- [ ] 2.5 Test `check_venue_unsafe` with a mocked `requests.Session` for each classification (ical, json-ld, ticketing, ai-extraction, no-website, social-only, robots-blocked, dead-domain, bot-blocked, unreachable), the WordPress `?ical=1` probe, a linked .ics that isn't a calendar, js_heavy, and the 404→homepage fallback recording the loaded URL; test that `check_venue` reports check-failed on an exception; verify that they pass
- [ ] 2.6 Test the command with `--state` and the inactive filter using a patched `check_venue`, and assert the CSV columns and the user agent; verify that the tests pass

## 3. Parsing and import

- [x] 3.1 Add `core/event_fetching/parsing.py` (iCal, JSON-LD, cleaning, placeholders, stable IDs) and the Scrapy spider (commit `8535366`); verified on the pilot
- [x] 3.2 Add `fetch_events` with pilot selection, `--all`, `--sheet-ids`, `--dry-run`, saving unapproved, keeping approval, escaping, price buckets and the 50-per-venue cap (commits `8535366`, `8ddf115`); verified on a full run: 1,634 created and 241 updated
- [x] 3.3 Fall back to AI extraction when an iCal feed can't be parsed (commit `8779da2`); verified on Luthier's Co-op
- [ ] 3.4 Add `core/tests/test_event_parsing.py` for `parse_ical` (cancelled entries, recurring instances with distinct IDs, all-day entries, placeholders) and `parse_json_ld` (nested and list nodes, performers vs title, offer price and URL, invalid block ignored, cancelled status); include `clean_text`, `clean_description` truncation and `is_placeholder`. Use small .ics and HTML fixtures under `core/tests/fixtures/events/`, and verify that the tests pass
- [ ] 3.5 Add spider callback tests using `TextResponse`/`HtmlResponse` from fixtures: iCal events emitted; a malformed iCal yields an error result and a request for the events page; ticketing listings follow at most 10 platform event links; a ticketing page without JSON-LD becomes an AI page; page text keeps absolute link URLs, drops scripts and is capped with `truncated`. Verify that the tests pass
- [ ] 3.6 Add `core/tests/test_fetch_events.py` with `CrawlerProcess` patched to fill results from fixtures. Cover: missing report error, `--all` selection, `--sheet-ids`, past events dropped, dedup across pages, the 50-event cap, new events unapproved with source/source_url/external_id set, re-run updating without duplicates, approval kept, description escaped (`<script>`), an over-long URL saved as empty, the `price_bucket` boundaries (0, 29.99, 30, 49.99, 50, 74.99, 75, None), a failed request reported per venue, and `--dry-run` saving nothing. Verify that every event-import scenario maps to a passing test

## 4. AI extraction

- [x] 4.1 Add `core/event_fetching/ai_extraction.py` with a JSON-schema output, prompt, validation and stable IDs, and parallel extraction in `fetch_events` (commit `8535366`); verified on the pilot pages against Opus
- [x] 4.2 Default to `claude-haiku-5-5` with `--model`, and send fallbacks only for supporting models (commit `d16c605`); verified on the full run
- [ ] 4.3 Add `core/tests/test_ai_extraction.py` with a mocked Anthropic client: a valid response is mapped to events (support act in artists, all-day when there is no time, the "$20 adv / $25 door" price parses to 20, "Free" parses to 0); an invalid date or placeholder is dropped; the "Jazz Jam" three dates get distinct IDs; a stop reason other than `end_turn` raises `ExtractionError`; fallback options are sent for opus/sonnet only; today's date is in the prompt. Verify that the tests pass
- [ ] 4.4 In `test_fetch_events.py`, test that AI pages are skipped with a note when `ANTHROPIC_API_KEY` is unset or `--skip-ai` is given, that an API error for one page is reported while other venues still save, and that token usage is reported. Verify that the tests pass

## 5. Integration

- [ ] 5.1 Run the full test suite (`python manage.py test`) and verify that it passes with no network access; then archive with `openspec archive add-venue-event-fetching`
