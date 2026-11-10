Issue: [#25 Look up new artists and bands on MusicBrainz every day](https://github.com/natea/newenglandmusic/issues/25)

## Why

Artist and band pages stay bare until someone runs `enrich_artists_from_musicbrainz` by hand: `/artists/amanda-palmer` shows only her band, with no bio, photo or links, although MusicBrainz knows her well. A band's lookup adds its members as new artists that wait for their own lookup, and neither scheduled job runs the command, so those members, and every act added since the last manual run, are never looked up.

## What Changes

- The daily job gains a step, `enrich_artists_from_musicbrainz --limit 100`, that looks up the bands and artists not yet looked up (bands first, so members a band adds are looked up on a later day).
- The limit keeps each run short and gentle on MusicBrainz (one request a second), so a backlog clears over several mornings, as the Spotify, Apple Music and YouTube steps' backlogs do.
- Records already looked up are not repeated: the step never uses `--refresh`.
- The step is not a new command: it uses the existing one as it is. A MusicBrainz rate limit stops the run, which keeps what it found, and the next morning carries on.
- PRODUCTION.md's schedule table and the daily script's header comment describe the new step.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scheduled-jobs`: the daily job runs nine commands, with the enrichment among them.
- `artist-records`: the enrichment from MusicBrainz also runs every day on the records not yet looked up, a limited number at a time.

## Impact

- `bin/daily.sh`, `PRODUCTION.md`, and the daily-job test in `core/tests/test_scheduled_jobs.py`; a test for the limit and ordering in `core/tests/test_artist_enrichment.py`.
- No model, migration, screen or new API key: the daily cron job already has the contact email and Last.fm key the command reads.
- Daily run time grows by about 4 to 7 minutes while a backlog lasts, then by a few seconds a day.
