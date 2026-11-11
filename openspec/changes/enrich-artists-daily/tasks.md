Issue: [#25 Look up new artists and bands on MusicBrainz every day](https://github.com/natea/newenglandmusic/issues/25)

## 1. Daily step

- [x] 1.1 Add `step python manage.py enrich_artists_from_musicbrainz --limit 100` after the YouTube matching in `bin/daily.sh`, with a comment saying why it runs last and is capped, and update the script's header comment. Verify: `core/tests/test_scheduled_jobs.py` `DAILY` lists the nine commands in order and `test_daily_run` passes.
- [x] 1.2 Add a test that a failing `enrich_artists_from_musicbrainz` step fails the daily run, naming the step, after the earlier steps ran (scenario "Enrichment fails"). Verify: the test passes.
- [x] 1.3 Add the step to PRODUCTION.md's schedule table (daily, after the YouTube matching; free; about 2 to 4 seconds a record, up to about 7 minutes; clears a backlog over several mornings; never refreshes). Verify: the table row reads correctly and the first `scheduled-jobs` requirement matches it.

## 2. Enrichment behaviour under a daily limit

- [x] 2.1 Add tests, using the MusicBrainz fixtures and no network, for: 130 unlooked records with `--limit 100` look up 100, bands before artists, leaving 30 ("More records than the limit"). Verify: the tests pass.
- [x] 2.2 Add tests for: a band's members are added unlooked and looked up by a later run ("A band's members"); a record left ambiguous is not retried ("Unmatched records are not retried"); records looked up before, whether matched, ambiguous or not found, cause no MusicBrainz request ("Already looked up"). Verify: the tests pass.
- [x] 2.3 Add a test that `MusicBrainzBusy` partway through stops the run, keeps earlier records, and the next run looks up only the remaining ones ("MusicBrainz asks to wait"), and that a record held for review is looked up but stays hidden. Verify: the tests pass.
- [x] 2.4 Run `venv/bin/python manage.py test` with the network blocked. Verify: the whole suite passes.
