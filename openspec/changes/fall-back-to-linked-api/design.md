## Context

- **`fetch_events` today:**
  - `select_targets` gives each venue one source.
  - Ticketmaster replaces iCal, ticketing and AI; Eventbrite replaces ticketing and AI. Neither replaces JSON-LD, and Eventbrite doesn't replace iCal.
  - API targets are fetched first. Crawl targets then go through the Scrapy spider, which returns results of kind `events`, `error` or `page`.
  - `page` results go to AI extraction. An unparseable iCal feed records an `error` and queues the venue's events page for AI extraction.
- **Problems:** notes starting with a `PROBLEM_PREFIXES` prefix count as problems on the job run and in the venue's fetch status.
- **What prompted this (2026-10-26):** on Render, The Main Pub's JSON-LD pages returned HTTP 403. Its Eventbrite organizer was linked, but the import never used it.

## Goals / Non-Goals

**Goals:**
- A linked venue whose feed or page fails on a run still gets its events from its API in that run.
- No extra API requests, and no change, for venues whose saved source works.
- The report shows what happened, without flagging a venue as failing when the fallback worked.

**Non-Goals:**
- Falling back for ticketing or AI venues: a linked API already replaces those sources.
- Remembering a failure between runs, or changing the saved source. A site that blocks one host may not block another, so each run decides afresh.
- Fallback for venues with no API link. They're reported as failing, as now.

## Decisions

**A source has failed when the crawl got no events and at least one error.** A feed that loads but has no upcoming events isn't a failure; the venue may have nothing on. Partial success, where some events came through, isn't a failure either. This uses what the spider already returns, so it needs no spider changes.

**The fallback runs after the crawl, before AI extraction.** The spider has to run first to know what failed, so the fallback can't be decided up front. For each failed target with a usable link, the API fetch is made with the same code as a normal API target (`fetch_from_ticketmaster` / `fetch_from_eventbrite`). The target's source is then switched to the API, so its events are saved, and its fetch status recorded, as from that API. Any `page` result queued for that venue, such as from an unparseable iCal feed, is dropped, so AI extraction doesn't also run for it.

**Order: Ticketmaster, then Eventbrite.** This is the same precedence as `select_targets`. Only one API is tried per venue: if the first linked one fails, the venue is reported as failing rather than trying the next. That keeps a run predictable, and two links on one venue are rare.

**Failure notes are reworded when the fallback works.** The crawl's `failed: <url> <error>` notes become `<source> failed, fetched from <api> instead: <url> <error>`, which doesn't start with a problem prefix. So the job run and the fetch status don't list the venue as failing, but the report still shows why the API was used. If the API fetch fails too, the original notes stay as they are, and the API's own `ticketmaster failed:` / `eventbrite failed:` note is added; both are problems.

**Replaced iCal events aren't removed on a fallback.** Ticketmaster's normal fetch deletes a venue's upcoming unapproved iCal events, because it replaces the feed. A fallback is for one run only, and the feed should work again, so its events are left alone.

## Risks / Trade-offs

- [A venue's feed lists more than its API, so a fallback run saves fewer events.] → It's only for runs where the feed failed, which would otherwise save none.
- [A feed fails every day on the server, and nobody notices, because the venue no longer counts as failing.] → The report notes it on every run. The venue's fetch status shows the API as its source, which differs from its saved source.

## Migration Plan

No migration. Released through `main`; the next scheduled or one-off fetch uses it.

**Rollback:** revert.

## Open Questions

None.
