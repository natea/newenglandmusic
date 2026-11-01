## 1. Before building

- [ ] 1.1 Back up the local database, and build in this change's own worktree and database; verify the dev server runs from the worktree.

## 2. Sources

- [ ] 2.1 Add `MusicAct.sources` with its migration and a `core/act_sources.py` label map (`ohb` → "Oh Hello Boston"); verify the migration applies and existing records have no sources.
- [ ] 2.2 Show sources in the artist and band admin lists and add a source filter; verify with an admin test for the "Filtering by source" scenario.

## 3. Import

- [ ] 3.1 Add `Instagram` and `YouTube` columns to `import_artists`; verify with a test for the "Instagram and YouTube columns" scenario and that the existing import tests still pass.
- [ ] 3.2 Build `import_act_list` (CSV and sheet, repeatable tabs merged into acts before lookup with conflicts reported, column aliases, state names, `--source`, `--dry-run`, `--limit`, review CSV, job run), deciding the kind by MusicBrainz ID or name and finding existing records first; verify with tests (mocked MusicBrainz, `core/tests/musicbrainz_fixture.py`) for every scenario in "Importing a curated list of names" and "Records remember the lists that name them".

## 4. Run it

- [ ] 4.1 Run Sooz's "In Rotation" and "2026 backlog" tabs together locally with `--dry-run`, then for real, then the enrichment; record the counts (made, found, reviewed) in this file and share the review CSV.
- [ ] 4.2 With approval, back up production and run the import and enrichment against it; verify the counts and a few band pages.

## 5. Finish

- [ ] 5.1 Run the whole suite with the network blocked and verify it passes, with every scenario in this change's spec covered.
- [ ] 5.2 Update `PRODUCTION.md` and the artists section of `AGENTS.md` for `import_act_list` and sources; verify both describe the shipped behavior.
