## Why

A full `fetch_events` run reports its problems only as lines in a plain-text report of several hundred venues. The run's summary says "venues with failures 21", but finding those 21 means scrolling through about 120,000 characters. There's also no way to see, from a venue, whether its events are being fetched at all. These are the things an admin needs to act on: re-link a venue to Ticketmaster, fix its source in the sheet, or check the site by hand.

## What Changes

- **Problems are saved as data.** A fetch's problems for a venue are saved with the venue they belong to: failed pages, Ticketmaster errors and AI extraction failures. Informational notes, such as "page text was truncated" or "not music, hidden from review", stay in the report only.
- **The job run page lists them up front.** A job run keeps its list of venues with problems. Its admin page shows that list above the text report, in red, with each venue linking to its admin page. The job run list shows each run's problem count, in red when there are any.
- **Each venue remembers its latest fetch.** That covers when it was fetched, which source was used, how many events were found and how many were upcoming, and any problems.
- **The venue admin shows that fetch status:**
  - an indicator column in the venue list
  - a filter: problems, nothing found, OK, never fetched
  - a section on each venue's page with the details and a link to the job run
- **Dry runs** list their problems on their job run, but don't change a venue's fetch status, since nothing was saved.

## Capabilities

### New Capabilities

- `venue-fetch-status`: recording each venue's latest fetch outcome and problems, and showing them on the venue admin and on the fetch's job run.

### Modified Capabilities

None. The fetch's printed report, and what it imports, are unchanged. This change builds on `record-job-runs` (the `JobRun` model and its admin), which must land first.

## Impact

- **Models:**
  - a new `VenueFetchStatus`, one-to-one with `Venue`
  - a `problems` field on `JobRun`
  - one migration
- **Code:**
  - `fetch_events` collects each venue's problems and saves its fetch status
  - `RecordedCommand` stores `self.job_problems`
- **Admin:**
  - `JobRunAdmin` gets a problems section and a problem-count column
  - `VenueAdmin` gets the fetch-status column, filter and section
- **No external services change.**
