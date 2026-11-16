Issue: [#57 Remove inactive bands from the public-facing Bands & Artists page](https://github.com/natea/newenglandmusic/issues/57)

## 1. Model and index

- [x] 1.1 Add `MusicAct.is_inactive` (default False, indexed) with one migration covering both `Band` and `Artist`
- [x] 1.2 Leave inactive acts out of `live_acts()` in `core/views/act_index.py`
- [x] 1.3 Tests: inactive acts left off `/bands` and its count; their pages, show links, search and sitemap still work; held and inactive are independent; the discovery deck test in `core/tests/test_discover.py` guards that inactive acts stay in the deck; update `core/tests/test_new_england_scope.py`'s use of `live_acts()` if needed

## 2. Admin and export

- [x] 2.1 Add the checkbox, list filter and "Mark inactive" / "Mark active" actions to `MusicActAdmin`; the actions use `queryset.update()`, and the form's `save_model` recording `is_inactive` in `field_sources` is harmless since nothing reads it
- [x] 2.2 Add `is_inactive` to the CSV export columns (`act-export`)
- [x] 2.3 Tests: the actions and filter; imports and enrichment leave the mark; the export column (and `test_act_export` passes); an exported file with the column still imports with `import_artists`

## 3. Command

- [x] 3.1 Write `mark_inactive_acts` as a `RecordedCommand` with slugs, saving with `queryset.update()` (optionally `bands/` or `artists/` qualified), `--file`, `--dry-run` and `--active`
- [x] 3.2 Tests: marking by slug, comments and blank lines in the file, dry run, unknown address, a slug in both kinds (ambiguous, nothing changed), a kind-qualified address, `--file`, the job run, a held act, reversing

## 4. Docs and rollout

- [ ] 4.1 Describe the inactive mark in `AGENTS.md`'s artists section
- [ ] 4.2 After deploy, run `mark_inactive_acts --dry-run` and then for real with `--file inactive-acts.txt` (copied from this change; its addresses carry the kind, since some are artists), and mark any it reports missing in the admin
