# Proposal

> Retroactive: this documents behavior already built on `venue-db` in commits `780440d`, `8535366`, `d16c605`, `8ddf115`, `8779da2` and `001bd3f`, so later changes such as `add-ticketmaster-discovery-api` have a baseline. Automated tests were added before it was archived.

## Why

The calendar depends on people submitting events by hand. That doesn't scale to roughly 700 venues across eleven states. Most venues already publish their schedule somewhere, but in many different forms. Some publish iCal feeds or schema.org data embedded in their pages. Some sell through ticketing platforms. Many just list shows in plain text. The site needs to find each venue's best source automatically, pull upcoming events from it, and queue them for review.

## What Changes

- **New `check_event_sources` command:**
  - It visits each active venue's website, respecting robots.txt, and finds its events listing page.
  - It classifies the venue's best source, in order of preference: an iCal feed (verified to contain events, including the WordPress Events Calendar `?ical=1` feed), schema.org JSON-LD events, links to a ticketing platform, or a page to send for AI extraction.
  - Venues it can't fetch are classified as no-website, social-only, robots-blocked, dead-domain, bot-blocked, unreachable or check-failed.
  - It writes `event_sources.csv`.
- **New `fetch_events` command:**
  - It reads the report and crawls venues with Scrapy, honouring robots.txt and throttling requests.
  - It parses iCal and JSON-LD directly, follows ticketing-platform event pages, and sends other pages to Claude for extraction.
  - It saves upcoming events unapproved for admin review.
- **New `Event` fields:** `source`, `source_url` and a unique `external_id`. Re-runs update events instead of duplicating them, and admin approvals are kept.
- **Fallbacks:**
  - A malformed iCal feed falls back to AI extraction of the venue's events page.
  - A dead URL in the sheet falls back to the site's homepage.
- **Claude Haiku 5.5** is the default extraction model, with `--model` to override it.
- **New dependencies:** `scrapy` and `anthropic`.

## Capabilities

### New Capabilities

- `event-source-detection`: works out, for each venue, whether and how its events can be fetched, and records that in a report.
- `event-import`: fetches venues' upcoming events from feeds, structured data and ticketing pages, and saves them to the review queue without duplicates.
- `ai-event-extraction`: extracts structured events from the text of a venue's web page with Claude, when there is no structured source.

### Modified Capabilities

None. There were no specs before this change.

## Impact

- **New code:**
  - `core/management/commands/check_event_sources.py`
  - `core/management/commands/fetch_events.py`
  - `core/event_fetching/` (`parsing.py`, `spider.py`, `ai_extraction.py`)
- **Model:** `Event` gains `source`, `source_url` and `external_id`, in migration 0076.
- **Dependencies:** `requirements.txt` adds `scrapy==2.19.0` and `anthropic==2.3.0`.
- **Configuration:** `ANTHROPIC_API_KEY` in `.env`. AI extraction is skipped without it.
- **External:** this fetches venues' websites with the user agent `venue-db-event-check/1.0`, and calls the Anthropic API. The first full run cost about $0.27.
