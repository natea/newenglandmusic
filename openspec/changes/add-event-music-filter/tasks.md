# Tasks

## 1. Model

- [ ] 1.1 Add `Event.kind` (choices: `live_music`, `dj_dance`, `open_mic`, `karaoke`, `comedy`, `other`; blank allowed), `Event.kind_set_by` (`ai`/`admin`, blank allowed) and `Event.MUSIC_KINDS`, with a migration; verify that it applies and reverses cleanly, and add a model test that `is_music_kind` is true for the three music kinds and for blank, and false for the rest

## 2. Labelling

- [ ] 2.1 Create `core/event_fetching/classification.py` with `KIND_DEFINITIONS` (one shared description of the kinds, including the party rule) and `classify(client, items, model)`, which batches 50 per request and returns a kind per item. Add `core/tests/test_classification.py` with a mocked client, covering: 120 items make 3 requests; the request uses a JSON schema with the kind enum; missing indexes and invalid kinds come back unlabelled; and a failed batch leaves only that batch unlabelled and is reported. Verify that the tests pass
- [ ] 2.2 Add `kind` to the AI extraction schema (enum) and prompt (from `KIND_DEFINITIONS`), and map it in `to_event_dict`; extend `test_ai_extraction.py` for a labelled event and for an invalid kind leaving the event unlabelled. Verify that the tests pass
- [ ] 2.3 Write `core/tests/evals/music_filter_eval.py`, a hand-run script (not part of the suite) that labels the spec's example titles plus 30 real titles from the database with the real model and prints mismatches. Run it once and record the result here

## 3. Import

- [ ] 3.1 In `fetch_events`, label events that are new, or unlabelled and not set by an admin, after deduplication and before saving; `save_event` writes `kind` unless an admin set it, and leaves the kind blank without `ANTHROPIC_API_KEY` or `--skip-ai`. Extend `test_fetch_events.py` with the classifier patched, covering: only new events are labelled; re-import makes no labelling request; an admin label survives; no key means saved unlabelled; and AI-extracted events skip batch labelling. Verify that the tests pass
- [ ] 3.2 Report per-kind counts and hidden events in the `fetch_events` output; verify with a test

## 4. Admin

- [ ] 4.1 Add a `KindListFilter` to `EventAdmin`, defaulting to music + unlabelled, with options for each kind, "all non-music" and "all"; add a "Kind" column. Test the default list, each option, and that approved non-music events stay approved; verify that the tests pass
- [ ] 4.2 Add "Mark as live music" and "Mark as not music (other)" actions that set `kind_set_by="admin"`; test both, and that a later import doesn't change them; verify that the tests pass

## 5. Backfill

- [ ] 5.1 Add `classify_events` (upcoming imported events, unlabelled, not admin-set) with `--dry-run`, `--limit` and `--model`, and a report of counts per kind plus hidden events by venue; test the selection, dry run, admin labels being skipped and a failed batch, and verify that the tests pass
- [ ] 5.2 Run `classify_events --dry-run`, logging to `logs/classify_events-<date>.log`, and review the hidden list with the user before the real run; then run it for real and record counts per kind
- [ ] 5.3 Run the full test suite with outbound network blocked and verify that it passes

## Workflow follow-up

- Archive after review, once every scenario has a passing test.
