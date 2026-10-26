## Why

Some venue websites block Render's servers but not a home connection. The Main Pub's JSON-LD fetch returns 403 on Render, so it gets no events there, even though it's linked to its Eventbrite organizer, whose API would give them. A linked API never replaces a venue's iCal feed or JSON-LD, because those usually list more, so nothing steps in when the feed or page fails. Now that the fetch runs on Render, every blocked venue with an API link loses its events the same way.

## What Changes

- **Fall back to the linked API when the saved source fails.** When a venue's iCal feed or JSON-LD fetch fails and yields no events, and the venue is linked to Ticketmaster or to an Eventbrite organizer, `fetch_events` fetches it from that API in the same run.
  - JSON-LD falls back to Ticketmaster first, then Eventbrite. An iCal venue linked to Ticketmaster is already fetched from Ticketmaster, so iCal falls back only to Eventbrite.
  - A venue whose saved source works is not sent to the API, so nothing changes for it.
  - `--skip-ticketmaster` and `--skip-eventbrite` turn off the fallback to that API too.
- **Reporting:** the venue's report says the saved source failed and which API was used instead.
  - When the fallback gets the events, the original failure is a note, not a problem. The venue isn't listed as failing on the job run or in its fetch status.
  - When the fallback fails too, both failures are problems.
  - The venue's fetch status records the API as its source for that run.
- **AI extraction is skipped** for a venue that falls back. An unparseable iCal feed already falls back to AI extraction of the events page; for a linked venue, the API is used instead, which is cheaper and exact.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `event-import`: a new requirement, "A failed feed falls back to the venue's linked API". The existing requirement that a linked API doesn't replace an iCal feed or JSON-LD still holds, because the fallback happens only when the feed or page fails.

## Impact

- **Code:** `core/management/commands/fetch_events.py` only: deciding which crawled venues failed, fetching them from their API after the crawl, and the notes. No model or migration changes.
- **Tests:** new `fetch_events` tests with the fake crawler returning errors, and mocked Ticketmaster and Eventbrite clients. No network.
- **Cost:** none to speak of: one API request per failing linked venue, and fewer AI extractions.
