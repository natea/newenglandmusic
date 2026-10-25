## Why

`check_event_sources` writes its findings to `event_sources.csv`, and `match_ticketmaster_venues` and `fetch_events` read that file. On Render, each cron job run starts on a fresh, empty disk, so a report written by the weekly check is gone before the daily fetch runs. The report needs to live in Postgres, which every job already shares. This is the second of the three blockers `PRODUCTION.md` lists before the scheduled jobs can run on a server.

## What Changes

- **New `VenueEventSource` model:** one row per checked venue.
  - **Fields:** what the check finds, i.e. the CSV's columns except the ones copied from the venue: URL, events page, best source, JSON-LD event count, iCal feed and event count, ticketing platforms, the JavaScript flag and the error.
  - **When it was checked:** a timestamp.
- **`check_event_sources` saves to the database.**
  - **Partial runs:** a run updates only the venues it checked, so a `--state` or `--limit` run no longer wipes the results for every other venue, as rewriting the CSV does today.
  - **Local review:** `--csv <path>` still writes the same CSV.
- **The readers use the database.** `match_ticketmaster_venues` and `fetch_events` read the saved sources instead of a file. Their `--report` option is removed (**BREAKING** for anyone calling it with that option).
- **Missing results:**
  - With no saved results at all, both commands fail with a message to run `check_event_sources` first, as they do today for a missing file.
  - A venue that has never been checked is treated like one with no usable source.
- **One-time import:** a new `import_event_sources <path>` command loads an existing `event_sources.csv`, so the 696 venues already checked locally don't need re-crawling.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `event-source-detection`: results are saved per venue in the database, a run updates only the venues it checked, a CSV export stays available, and an existing CSV can be imported.
- `event-import`: venues are selected from the saved sources, and the missing-report error now means no source check has been saved.
- `ticketmaster-venue-linking`: the default selection reads the saved sources' ticketing platforms.

## Impact

- **Model:** a new `VenueEventSource`, one-to-one with `Venue` and deleted along with it, in one migration. `Venue` itself doesn't change, so saving a source never calls `Venue.save()`, which would re-render every one of the venue's events.
- **Changed code:**
  - `check_event_sources`: saves results, and adds `--csv`.
  - `fetch_events.select_targets`: reads the model.
  - `match_ticketmaster_venues.ticketmaster_sheet_ids`: reads the model.
- **New command:** `import_event_sources`.
- **Docs:** `PRODUCTION.md` and the command docstrings drop the report file.
- **No external services change:** the crawl, Ticketmaster and Anthropic calls stay as they are.
