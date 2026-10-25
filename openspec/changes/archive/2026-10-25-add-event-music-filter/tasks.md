# Tasks

## 1. Model

- [x] 1.1 Add `Event.kind` (choices: `live_music`, `dj_dance`, `open_mic`, `karaoke`, `comedy`, `other`; blank allowed), `Event.kind_set_by` (`ai`/`admin`, blank allowed) and `Event.MUSIC_KINDS`, with a migration; verify that it applies and reverses cleanly, and add a model test that `is_music_kind` is true for the three music kinds and for blank, and false for the rest

## 2. Labelling

- [x] 2.1 Create `core/event_fetching/classification.py` with `KIND_DEFINITIONS` (one shared description of the kinds, including the party rule) and `classify(client, items, model)`, which batches 50 per request and returns a kind per item. Add `core/tests/test_classification.py` with a mocked client, covering: 120 items make 3 requests; the request uses a JSON schema with the kind enum; missing indexes and invalid kinds come back unlabelled; and a failed batch leaves only that batch unlabelled and is reported. Verify that the tests pass
- [x] 2.2 Add `kind` to the AI extraction schema (enum) and prompt (from `KIND_DEFINITIONS`), and map it in `to_event_dict`; extend `test_ai_extraction.py` for a labelled event and for an invalid kind leaving the event unlabelled. Verify that the tests pass
- [x] 2.3 Write `core/tests/evals/music_filter_eval.py`, a hand-run script (not part of the suite) that labels the spec's example titles plus 30 real titles from the database with the real model and prints mismatches. Run it once and record the result here
  - Result (2026-10-25, claude-haiku-5-5, about 4,500 input tokens): all 16 spec examples labelled as expected, including the user's examples (trivia, Nerd Night, clown class, print club, karaoke, comedy, Santa, fiber artists, dance lessons) and the Jerry Garcia and Brass Against Halloween shows.
  - The 30-event real sample looked right: bingo, speed-dating, a thrift sale, an art display and swing lessons came out `other`; open mics and Irish sessions came out music.
  - Worth knowing: "Live Band Karaoke" is labelled `karaoke`, so it's hidden, per the user's rule. "Jon Spencer (18+)", a rock musician, came out `dj_dance`, which is wrong but still music, so he stays visible.

## 3. Import

- [x] 3.1 In `fetch_events`, label events that are new, or unlabelled and not set by an admin, after deduplication and before saving; `save_event` writes `kind` unless an admin set it, and leaves the kind blank without `ANTHROPIC_API_KEY` or `--skip-ai`. Extend `test_fetch_events.py` with the classifier patched, covering: only new events are labelled; re-import makes no labelling request; an admin label survives; no key means saved unlabelled; and AI-extracted events skip batch labelling. Verify that the tests pass
- [x] 3.2 Report per-kind counts and hidden events in the `fetch_events` output; verify with a test

## 4. Admin

- [x] 4.1 Add a `KindListFilter` to `EventAdmin`, defaulting to music + unlabelled, with options for each kind, "all non-music" and "all"; add a "Kind" column. Test the default list, each option, and that approved non-music events stay approved; verify that the tests pass
- [x] 4.2 Add "Mark as live music" and "Mark as not music (other)" actions that set `kind_set_by="admin"`; test both, and that a later import doesn't change them; verify that the tests pass

## 5. Backfill

- [x] 5.1 Add `classify_events` (upcoming imported events, unlabelled, not admin-set) with `--dry-run`, `--limit` and `--model`, and a report of counts per kind plus hidden events by venue; test the selection, dry run, admin labels being skipped and a failed batch, and verify that the tests pass
- [x] 5.2 Run `classify_events --dry-run`, logging to `logs/classify_events-<date>.log`, and review the hidden list with the user before the real run; then run it for real and record counts per kind
  - Dry run (2026-10-25): 2,272 events, 406 would be hidden. The user reviewed the hidden list; about 4 looked like real shows.
  - Real run (2026-10-25, claude-haiku-5-5, 273,858 input / 41,566 output tokens): 2,260 events labelled: 1,657 live_music, 101 dj_dance, 95 open_mic, 327 other, 57 comedy, 23 karaoke. 407 hidden.
  - Labels aren't fully repeatable between runs: of the 4 suspect events, Steven Page Trio came out live_music and Synthfest Session 1 dj_dance this time. The other two, "Band Halloween: Coat Drive & Fundraiser" (pk 109) and "Student Concert" (pk 202), were relabelled live_music with `kind_set_by=admin`, at the user's request.
- [x] 5.3 Run the full test suite with outbound network blocked and verify that it passes

## Workflow follow-up

- Archive after review, once every scenario has a passing test.
