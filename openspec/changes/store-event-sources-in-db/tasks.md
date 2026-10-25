## 1. Model

- [ ] 1.1 Add `VenueEventSource` to `core/models.py`, as in design.md: a one-to-one link to `Venue` (cascade, `related_name="event_source"`), `checked_at`, `BestSource` choices, an array of `platforms` and a boolean `js_heavy`. Verify that `makemigrations` creates one migration and that `migrate` applies it.
- [ ] 1.2 Create `core/event_sources.py` with:
  - `save_event_source(venue, result)`: a check result dict becomes model fields, through `update_or_create` and never `Venue.save()`.
  - `event_source_row(source)`: model to the row dict that the readers use.
  - `event_source_csv_row(source)`: model to the old CSV columns, with platforms `;`-joined and `js_heavy` as `"yes"`/`""`.

  Verify with the tests in 1.3.
- [ ] 1.3 Write tests in `core/tests/test_event_sources.py`, verified when they pass:
  - a round trip from result dict to model to CSV row, with every column;
  - saving twice keeps one row per venue;
  - saving leaves the venue's fields and its events' `baked_html_template` unchanged (scenario "Venue's own fields untouched").

## 2. Source check saves to the database

- [ ] 2.1 Change `check_event_sources` to save every result through `save_event_source`, in one transaction after the crawl. Replace `--output` with an optional `--csv <path>`, which writes this run's results in the old column order. Update the module docstring. Verify with the tests in 2.2.
- [ ] 2.2 Update `core/tests/test_check_event_sources.py`, with `check_venue` patched to return canned results, verified when the tests pass. Cover the scenarios first check of a venue, re-check replaces the result, partial run keeps other results, state filter (only NH results change) and CSV export. Check that the existing crawler tests, which mock `requests`, still pass.

## 3. One-time CSV import

- [ ] 3.1 Add `import_event_sources <path> [--dry-run]`:
  - matches rows to venues by `sheet_id`;
  - saves through `save_event_source`, with `checked_at` set to the file's modification time;
  - reports how many results it created, replaced and skipped (unknown sheet IDs).

  Write a module docstring showing how to run it. Verify with the tests in 3.2.
- [ ] 3.2 Write tests in `core/tests/test_import_event_sources.py`, using a temporary CSV, verified when they pass. Cover the scenarios import an existing report (3 saved, 1 unknown skipped, nothing crawled: `requests` patched to fail if called) and import dry run.

## 4. Readers use the saved results

- [ ] 4.1 Change `fetch_events.select_targets` to build its rows from `VenueEventSource` through `event_source_row`. Raise "run check_event_sources first" when no results exist, and remove `--report`. Update the docstring. Verify with the tests in 4.3.
- [ ] 4.2 Change `match_ticketmaster_venues` so its default selection uses `platforms__contains=["ticketmaster"]`. With no results and no `--sheet-ids` or `--all`, it raises the existing error. Remove `--report` and update the docstring. Verify with the tests in 4.4.
- [ ] 4.3 Update `core/tests/test_fetch_events.py`: replace `report_row`/`write_report` with a `make_source` helper. Add tests for the scenarios missing report (no saved results) and venue never checked. Verify that the whole file passes, Ticketmaster and AI scenarios included, with their existing mocks.
- [ ] 4.4 Update `core/tests/test_match_ticketmaster_venues.py` for saved results: the default selection and explicit venues still pass, and add the scenario no saved results. Verify that the tests pass with `TicketmasterClient` mocked.

## 5. Docs and data

- [ ] 5.1 Update `PRODUCTION.md`:
  - remove blocker 2 from "Before the jobs can run on a server";
  - drop `--output`/`--report` from the job table;
  - add a step to the database-loading instructions: run `import_event_sources` before dumping.

  Verify by reading the section.
- [ ] 5.2 Update `AGENTS.md` ("The pipeline" step 3 says the check "writes `event_sources.csv`") to say it saves results in the database, with `--csv` for a file. Verify by reading it.
- [ ] 5.3 Run `venv/bin/python manage.py test` with outbound network blocked, and verify the whole suite passes.
- [ ] 5.4 Locally, run `import_event_sources event_sources.csv --dry-run` and then a real run, logged to `logs/import_event_sources-YYYY-MM-DD.log`. Verify that about 696 results are saved. Then run `fetch_events --dry-run --per-source 1` and verify that it selects venues from the saved results.
