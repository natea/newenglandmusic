## 1. Deciding the kind

- [ ] 1.1 Add `choose_kind(name, matcher)` to `core/artist_enrichment.py`, returning the kind and MusicBrainz ID, or a review reason. Verify with tests for a band, a person, both, several with no evidence, and not found.

## 2. The command

- [ ] 2.1 Add `import_artists_from_events` (`--limit`, `--dry-run`, `--review-csv`, a `JobRun`): collect names from approved events' Artists column, counted, most-named first, skipping placeholders and existing records; make the settled ones; write the review CSV. Verify with tests for each spec scenario, including a busy MusicBrainz stopping the run and the review CSV imported by `import_artists`.

## 3. Docs and check

- [ ] 3.1 Document the command in PRODUCTION.md's "Artists and bands" section, and keep its review CSVs out of git. Run the whole suite with outbound network blocked. Then run it locally with `--dry-run --limit 50` and check a sample of its decisions by hand.
