## 1. Before building

- [x] 1.1 Back up the local database, and build in this change's own worktree and database; verify the dev server runs from the worktree.

## 2. Sources

- [x] 2.1 Add `MusicAct.sources` with its migration and a `core/act_sources.py` label map (`ohb` → "Oh Hello Boston"); verify the migration applies and existing records have no sources.
- [x] 2.2 Show sources in the artist and band admin lists and add a source filter; verify with an admin test for the "Filtering by source" scenario.

## 3. Review queue

- [x] 3.0 Add `needs_review` and `review_reasons` with their migration; hide held acts (404 on their page, left out of `names_to_records()` and the sitemap); add the admin's "Needs review" filter, reasons column and "Mark ready" action that relinks their events; verify with tests for every scenario of "Acts held for review stay off the site".

## 4. Import

- [x] 3.1 Add `Instagram` and `YouTube` columns to `import_artists`; verify with a test for the "Instagram and YouTube columns" scenario and that the existing import tests still pass.
- [x] 3.2 Build `import_act_list` (CSV and sheet, repeatable tabs merged into acts before lookup with conflicts reported, column aliases, state names, `--source`, `--dry-run`, `--limit`, holding unsettled acts for review with their reasons, linking approved events afterwards, job run), deciding the kind by MusicBrainz ID or name and finding existing records first; verify with tests (mocked MusicBrainz, `core/tests/musicbrainz_fixture.py`) for every scenario in "Importing a curated list of names" and "Records remember the lists that name them".

## 5. Run it

- [x] 4.1 Run Sooz's "In Rotation" and "2026 backlog" tabs together locally with `--dry-run`, then for real, then the enrichment; record the counts (made live, made held for review, found) in this file.
  - 2026-10-31, `logs/act-list-ohb-2026-10-31.log`: the dry run read 554 acts from both tabs. The full local run was cut off (the local Postgres stopped at 21:13) and left no counts; a 60-act sample on the test site made 35 live, held 23 for review and found 2 (28 problems, all differing values between the tabs), and its enrichment recorded 79 records. The full list then ran on production (4.2).
- [x] 4.2 With approval, back up production and run the import and enrichment against it; verify the counts and a few band pages.
  - 2026-10-31, backup `render-2026-10-31-2219-before-ohb-import.dump`, `logs/act-list-ohb-production-2026-10-31.log`: 554 acts; made live 310, held for review 227, found 17, problems 10 (nine differing values between the tabs, one MusicBrainz ID differing from the record's), events linked 1,313. Enrichment of 558 records: 365 matched on MusicBrainz (88 with a Wikipedia introduction), 184 not found, 9 ambiguous; no errors. Band pages checked live on 2026-11-01 (`/bands` lists 3,749 acts).

## 6. Finish

- [x] 5.1 Run the whole suite with the network blocked and verify it passes, with every scenario in this change's spec covered.
  - 2026-10-31: 1,390 tests passed offline before the merge (`f76ac2f`); 1,435 on `main` since.
- [x] 5.2 Update `PRODUCTION.md` and the artists section of `AGENTS.md` for `import_act_list` and sources; verify both describe the shipped behavior.
