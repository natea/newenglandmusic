## 1. Deciding the kind

- [x] 1.1 Add `choose_kind(name, matcher)` to `core/artist_enrichment.py`, returning the kind and MusicBrainz ID, or a review reason. Verify with tests for a band, a person, both, several with no evidence, and not found.

## 2. The command

- [x] 2.1 Add `import_artists_from_events` (`--limit`, `--dry-run`, `--review-csv`, a `JobRun`): collect names from approved events' Artists column, counted, most-named first, skipping placeholders and existing records; make the settled ones; write the review CSV. Verify with tests for each spec scenario, including a busy MusicBrainz stopping the run and the review CSV imported by `import_artists`.

## 3. Events link to their performers

- [x] 3.1 Add `EventPerformer` (event, artist or band, order, source) with its constraints and a migration. Verify with model tests for the artist-or-band check and no performer twice, and that `makemigrations --check` is clean.
- [x] 3.2 Add `core/event_performers.link_from_names`, and call it from `import_artists_from_events` for every approved event and from `fetch_events.save_event` for each saved event (not in a dry run). Verify with tests for several acts in order, a name with no record, two records with one name, the text changing, an editor's performer kept, and fetched events linked.
- [x] 3.3 Add the performers inline to the event admin, with autocomplete for artists and bands, and new rows marked as the editor's. Verify with an admin test adding, reordering and removing a performer.

## 4. Docs and check

- [x] 4.1 Document the command and the performers in PRODUCTION.md's "Artists and bands" section, and keep its review CSVs out of git. Run the whole suite with outbound network blocked. Then run it locally with `--dry-run --limit 50` and check a sample of its decisions by hand.
