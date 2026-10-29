## 1. Lookup

- [ ] 1.1 Add `core/neighborhoods.py`:
  - a Nominatim search client and an Overpass client, with an injectable session, sleep and clock;
  - one Nominatim request a second;
  - Overpass retries and a mirror;
  - the contact user agent;
  - the name-choosing rules, with the skip list.
  
  Add fixtures in `core/tests/fixtures/osm/`. Verify with tests for:
  - suburb preferred;
  - historic district skipped;
  - only the borough;
  - Williamsburg;
  - Overpass busy;
  - paced;
  - Google data never sent.
- [ ] 1.2 Add `neighborhood`, `neighborhood_source` and `neighborhood_checked_at` to `Venue`, with a migration. Verify that `makemigrations --check` is clean.
- [ ] 1.3 Add the `lookup_venue_neighborhoods` command (`RecordedCommand`), with `--limit` (default 300), `--sheet-ids` and `--dry-run`. It finds venues by name and town, saves with `update()`, re-renders only changed venues, and stops on Nominatim 429 or 403. Verify with tests for:
  - venue found;
  - a different place with the town's name;
  - Nominatim blocks;
  - changed;
  - due rules (never looked up, a year old, editor kept).

## 2. Showing and editing

- [ ] 2.1 Show " (<neighborhood>)" after the venue's town in `event.html`. Verify with render tests for shown, no neighborhood, and a venue override.
- [ ] 2.2 Add the neighborhood fields to the venue admin: source filter, editable value, a "no neighborhood" option, and a re-render on save. Verify with an admin test for an editor setting one, and a later run keeping it.
- [ ] 2.3 Add the "© OpenStreetMap contributors" footer credit and the `/privacy` data-source line. Verify with render tests.

## 3. Neighborhood filter

- [ ] 3.1 Add `neighborhood` to `core/geo_filters.py`: parsing, validation against the chosen towns, `q()`, `query_string` and the cookie. Add the multi-select to the filter form, and generalize `town_chips.js` to it. Verify with render tests for two neighborhoods, no town chosen, and a neighborhood from another town. Add a Playwright test of the neighborhood chips.

## 4. Jobs and docs

- [ ] 4.1 Add `lookup_venue_neighborhoods` to `bin/weekly.sh`, and update `WEEKLY` in `core/tests/test_scheduled_jobs.py`. Add the command, its services and its credit to PRODUCTION.md and AGENTS.md. Verify that the scheduled-jobs tests pass with four weekly steps.

## 5. Check

- [ ] 5.1 Run the whole suite with outbound network blocked. Then run `lookup_venue_neighborhoods --dry-run --limit 30` locally, check the names by hand, and record the share of city venues found in the design's open question. Verify that the tests pass and the names are right.
