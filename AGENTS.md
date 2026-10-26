# AGENTS.md

Guidance for coding agents working in this repository. `CLAUDE.md` is a symlink to this file.

## What this is

This checkout started as [nyc noise](https://nyc-noise.com/), a Django NYC music calendar. On `main` (which grew out of the `venue-db` branch) it is being turned into a **Northeast US music venue database and event calendar**. Venues come from a Google Sheet; their events are fetched from venue websites, ticketing platforms and APIs.

- **Two remotes, and only one to push to:**
  - **`origin`:** the upstream `nycnoise/nycnoise` repo. Never push or open pull requests there.
  - **`github`:** this site's own public repo, [natea/newenglandmusic](https://github.com/natea/newenglandmusic). Render deploys its `main` branch, so push only when asked.
- Commit locally, on a branch, when asked. `main` is what deploys; see `PRODUCTION.md`.
- The schema has diverged from nycnoise on purpose. Don't keep NYC-specific fields or behavior for compatibility.

## Running it

- **Python:** Python 3.11 in `venv/`. Install packages with `uv pip install`, never `pip`. Dependencies are pinned in `requirements.txt`.
- **Postgres:** runs locally from `~/.local/share/nycnoise-pgdata` on port 5432, database `nycnoise`. Start it with `pg_ctl -D ~/.local/share/nycnoise-pgdata -l ~/.local/share/nycnoise-pgdata/server.log start`.
- **Dev server:** `venv/bin/python manage.py runserver 8001`. Use port 8001, because 8000 is taken by another tool's OAuth callback.
- **Tests:** `venv/bin/python manage.py test`.

## Secrets

API keys live in `.env`, which is git-ignored:
- `ANTHROPIC_API_KEY`
- `TICKETMASTER_API_KEY` (the Ticketmaster app's Consumer Key)
- `EVENTBRITE_API_KEY` (an Eventbrite account's private token)
- `GOOGLE_PLACES_API_KEY` (restricted to the Places API (New))

`.env.example` lists them. Never print, log or commit a key; check only whether one is set. Pass keys in headers rather than URLs where the API allows it, and keep them out of error messages and test fixtures.

## Data sources

- **Venues come from the Google Sheet copy** "Northeastern US Music Venues - v3 (venue-db copy)" (`1QBzKHOUWOR0Fw0ODrwEep5eGfZg4SmTUq4PsaCbbnGQ`, tab "V3 - Flattened"). Rows are keyed by its `Venue_ID` column. Don't modify the original sheet (`14s8oWNJbRNWn7jys675u_t8B9A8nXyuAVkBhzyE4l2M`).
- **Read Google Sheets with the `gog` CLI,** not an MCP server. If it reports `invalid_grant`, the user must re-authorize: `gog auth add <your-google-account> --services calendar,drive,gmail,sheets`.
- **On a server, the sheet sync reads the sheet with a service account** instead, when `GOOGLE_SERVICE_ACCOUNT_JSON` is set (`core/google_sheets.py`; setup in `PRODUCTION.md`). Never print or log that variable.
- **The sheet's coordinates are town centres,** not venue locations. Use `Venue.exact_location`, which is the Google Places location when that match is confident.

## The pipeline

These are management commands, run in this order:

1. **`sync_venues_from_gsheets`:** reads the sheet into `Venue`. It never deletes venues, and it never touches fields that don't come from the sheet (`place_*`, `ticketmaster_venue_id`, `eventbrite_organizer_id`).
2. **`lookup_venue_places`:** finds each venue on Google Places and records its place ID and exact coordinates. Google's terms allow storing nothing else, and the coordinates for only 30 days: `--refresh-stale` refreshes them by place ID, and every run deletes any older than 30 days.
3. **`check_event_sources`:** works out how each venue's events can be fetched (iCal, JSON-LD, ticketing pages, AI extraction) and saves the answer per venue in the database (`VenueEventSource`), which the next two commands read. `--csv <path>` also writes a file to read; `import_event_sources <path>` loads an old one.
4. **`match_ticketmaster_venues`** and **`match_eventbrite_organizers`:** link venues to Ticketmaster venues and to their Eventbrite organizers, found from the Eventbrite links on their own pages.
5. **`fetch_events`:** fetches upcoming events, from a linked API (Ticketmaster first, then Eventbrite) or else the saved source, falling back to a linked API when a feed or JSON-LD page fails, and saves new ones **unapproved**, for review at `/admin/core/alleventproxy/`. `Event.objects` returns approved events only; use `Event.all_objects` for everything.

On Render, two cron jobs run them on a schedule: `bin/daily.sh` and `bin/weekly.sh`, defined in `render.yaml` (see `PRODUCTION.md`). A step that fails doesn't stop the later ones, but fails the run. Each run of these commands is recorded as a `JobRun` (`core/job_runs.py`) and listed at `/admin/core/jobrun/`. A new pipeline command should subclass `RecordedCommand` and set `self.job_summary`.

### Logs

Write the output of long command runs to `logs/`, never to a temporary or scratch directory, because the user tails these files.
- **Google Places venue matching** (`lookup_venue_places`): append to `logs/lookup_venue_places.log`, which already holds earlier runs. Start each run with a dated header line, for example:
  `echo "=== lookup_venue_places $(date '+%Y-%m-%d %H:%M')" >> logs/lookup_venue_places.log && venv/bin/python manage.py lookup_venue_places >> logs/lookup_venue_places.log 2>&1`
- **Other runs** (`fetch_events`, `check_event_sources`): use a dated file such as `logs/fetch_events-YYYY-MM-DD.log`.
- `*.log` files are git-ignored.

## Paid and rate-limited APIs

- **Anthropic:** event extraction defaults to `claude-haiku-5-5`. A full `fetch_events --all` run costs about $0.30.
- **Ticketmaster Discovery API:** free, limited to 5 requests per second and 5,000 per day.
- **Eventbrite API:** free, limited to 2,000 requests an hour per token. The client waits half a second between requests.
- **Google Places Text Search:** 5,000 free calls a month for the default fields, and 1,000 with `--contact`. Rerunning lookups for every venue uses up that allowance, so look up only venues that need it.
- **Ask before a run that spends money** beyond a small sample. Prefer `--dry-run` and `--limit` / `--sheet-ids` first.
- **Crawl politely:** obey robots.txt and send the honest user agent `venue-db-event-check/1.0`. Repeated full crawls get the crawler blocked.

## Specs and tests (OpenSpec)

- **Propose every major change before building it.** Create an OpenSpec proposal (`/opsx:propose`) for any major change: a new feature, capability or data source; a model or schema change; a new external API; or a change to behavior a spec in `openspec/specs/` describes. Implement only after the user has reviewed it, with `/opsx:apply` and then `/opsx:archive`. Small bug fixes and minor tweaks don't need a proposal, but they still need tests. If unsure, ask.
- **OpenSpec layout:** plans live in `openspec/` (spec-driven schema), and the main specs in `openspec/specs/` describe current behavior.
- **A feature is complete only when every spec scenario has a passing automated test.** Don't archive a change until it does and all its tasks are checked.
- **Tests never touch the network.** Mock Google Sheets (`gog`), venue websites, Anthropic, Ticketmaster, Eventbrite and Google Places, or replay recorded fixtures with the keys stripped (`core/tests/fixtures/`). The suite must pass with outbound network blocked.
- **When a real run contradicts the design**, update the change's design and tasks. Don't paper over it in code.

## Code style

Match the surrounding code: lowercase comments and docstrings that say *why*, module docstrings that show how to run a command, and small focused functions. Save a venue with `queryset.update()` when its events don't need re-rendering: `Venue.save()` re-renders the stored HTML of every one of its events.
