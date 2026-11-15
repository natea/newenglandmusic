Issue: [#25 Look up new artists and bands on MusicBrainz every day](https://github.com/natea/newenglandmusic/issues/25)

## Context

`enrich_artists_from_musicbrainz` already does the whole job: it takes bands then artists that have no `musicbrainz_checked_at` (`core/artist_enrichment.py`'s `due`), looks each up, fills in the introduction, photo and links, adds a band's members as artists, and stamps `musicbrainz_checked_at`. It accepts `--limit`, skips records checked before unless `--refresh`, stops on `MusicBrainzBusy` keeping earlier records, and records itself as a `JobRun`. Neither `bin/daily.sh` nor `bin/weekly.sh` runs it, so only a person does. The daily cron job already receives `API_CONTACT_EMAIL` (MusicBrainz's user agent) and `LASTFM_API_KEY` (evidence for shared names) from the web service, so no key changes. See proposal.md for the motivation.

## Goals / Non-Goals

**Goals:**
- Records not yet looked up get looked up without anyone running a command.
- A fixed daily cap bounds run time and MusicBrainz load.

**Non-Goals:**
- No code in the command itself changes (no new options, no ordering change).
- No scheduled `--refresh` of records already looked up, so stale data stays until an editor or a manual run refreshes it.
- No scheduled `import_artists_from_events` or `import_act_list`: making records from new events' artist names stays manual, so this step only enriches records that exist.
- Records marked ambiguous or not found are not retried automatically.

## Decisions

- **Add one step to `bin/daily.sh`, not the weekly script.** The issue asks for the daily job, and the daily cap clears a backlog sooner than a weekly one would. Alternative: weekly with a larger limit; rejected, since a weekly run of hundreds of records at 2 seconds each is long for the 512 MB cron job.
- **`--limit 100`.** The docstring says about 2 seconds a record, plus about 2 more requests (about 2 more seconds) for those with a Wikidata item and 1 or 2 for the photo, so 100 records take roughly 4 to 7 minutes, comparable to the Spotify step's 4 minutes. A hundred a day clears a backlog of several hundred in a few days, and later days handle only new records. Alternatives: 50 (slower backlog) or 300 (the Last.fm step's size, up to 20 minutes).
- **Last in the daily order.** It depends on nothing before it in the job, and nothing before it depends on it, so putting it last means a slow run or a MusicBrainz block delays no play-button matching. The existing steps keep their order. Alternative: right after `fetch_events`; rejected for that reason.
- **Never `--refresh`.** `due` already limits a default run to records with no `musicbrainz_checked_at`, which is exactly the issue's "haven't been looked up yet". Records an editor clears (the admin sets the stamp to empty) or an import resets are picked up again by the same rule.
- **Members wait for a later run or fill remaining room.** The command builds its list of records before it starts, so members added during a run are not in it; they are looked up the next morning. The issue's own wording accepts this.
- **No changes to failure handling.** The step script already lets a failed step fail the run without stopping others (`bin/steps.sh`), and a `MusicBrainzBusy` stop exits normally with its summary in the `JobRun`.

## Tests and mocking

No test touches the network. The daily-script test uses the existing stub in `core/tests/test_scheduled_jobs.py` standing in for Python, so it checks only the order of commands. The enrichment tests use the MusicBrainz, Wikidata and Wikipedia replays in `core/tests/musicbrainz_fixture.py` (and the existing Last.fm mock), as `core/tests/test_artist_enrichment.py` already does. The limit and ordering scenarios build records in the test database and run the command with the same fixtures; the "MusicBrainz asks to wait" scenario makes the fixture raise `MusicBrainzBusy`. No real request goes to MusicBrainz, Wikidata, Wikipedia, Wikimedia Commons or Last.fm.

## Risks / Trade-offs

- A first run clears only 100 records, so the pages stay bare for days on a big backlog → accepted; reported in the `JobRun` counts, and the limit can be raised.
- A run of 100 is longer than the others in a bad MusicBrainz hour → the busy stop keeps what was found, and the cron job is billed by the second, so the extra cost is small.
- Records the matcher can't settle stay unmatched, with the bare page the issue complains about → they show in the admin as ambiguous or not found for an editor to settle; automatic retries are out of scope.

## Migration Plan

Merge to `main`; the next daily run after Render deploys it carries out the step. Roll back by removing the line from `bin/daily.sh`; records already looked up keep their data.

## Open Questions

- Should members' and new acts' records also be made automatically from new events' artist names (`import_artists_from_events`, which needs a review step for names MusicBrainz can't settle)? This change leaves it out.
- Is 100 a day the right size once the backlog is seen? It can be changed later without changing the specs' behaviour, but the scenarios use 100.
