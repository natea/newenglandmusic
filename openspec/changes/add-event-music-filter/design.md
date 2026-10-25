# Design

## Context

See proposal.md. Every source produces the same event dict (`core/event_fetching/parsing.py`), and `save_event` in `fetch_events` is the only code that writes imported events. AI extraction already sends a JSON schema to Claude Haiku 5.5 with low effort (`ai_extraction.py`). The event admin (`EventAdmin`, registered for `AllEventProxy`) lists every event, with a custom start-time filter that defaults to "Future". `Event.objects` returns approved events only, and the public site shows only approved events.

## Goals / Non-Goals

**Goals:**
- Label every imported event cheaply, and only once.
- Keep non-music events out of the review queue without ever deleting one.
- Let a person correct any label, permanently.

**Non-Goals:**
- Labelling events that people submit through the site's form. They're already curated and keep an empty kind.
- Genres or other sub-labels within music.
- Hiding approved events from the public site. Approval stays the human decision.

## Decisions

**1. Add `Event.kind` (blank, or one of six choices) and `Event.kind_set_by` (`ai` or `admin`).**
- Blank means unlabelled. Unlabelled events are treated like music for visibility, so a missing key or a failed request never hides anything.
- `Event.MUSIC_KINDS = {"live_music", "dj_dance", "open_mic"}`.
- **Alternative: a boolean `is_music`.** Kinds cost the same to produce and let an admin see why an event was hidden. A boolean would also force the borderline calls (karaoke, open mic) into the data, when it's better to keep them as a list we can change.

**2. AI-extracted events are labelled inside the extraction call.**
- `EVENTS_SCHEMA` gets a `kind` property with an `enum` of the six values, so structured output can only return valid kinds. The prompt gets one short paragraph defining the kinds, including the party rule.
- It costs no extra request: the model already reads the page.

**3. Other sources are labelled in batches.**
- **Module:** `core/event_fetching/classification.py`.
- **Function:** `classify(client, items, model)`, where `items` is a list of `(venue_name, location, title, artists, description[:300])`.
- **Request:** batches of at most 50 numbered items go to Claude Haiku 5.5 with low effort and a JSON schema of `{"labels": [{"index": int, "kind": enum}]}`.
- **Return value:** a kind per index. Missing indexes, or an error for the batch, mean unlabelled.
- **Why:** titles alone are often enough; a short description and the venue settle the rest. Fifty per call keeps the input small and limits how much a failed call can affect.
- **Alternative: keyword rules first and the model for the rest.** Measured on current data, keywords misfire on real shows ("Halloween Tour", "World Class Music"), so they would need the model's review anyway.

**4. Label in `fetch_events` after deduplication and before `save_event`, and only events that need it.**
- An event is labelled when it doesn't exist yet, or exists with a blank kind and `kind_set_by != "admin"`.
- AI-extracted events arrive already labelled.
- `save_event` writes `kind` only when the existing kind wasn't set by an admin.
- **This keeps re-runs nearly free:** only new events are sent for labelling.

**5. Review list: a custom `KindListFilter` on `EventAdmin`, defaulting to "music + unlabelled".**
- It follows the existing `StartTimeListFilter` pattern for defaults. The other options are each kind, "all non-music" and "all".
- **Actions:** "Mark as live music" and "Mark as not music (other)". Both set `kind_set_by = "admin"`, and they save through `.update()` on `Event.all_objects`.
- **A "Kind" column** shows the label.

**6. Backfill with `classify_events`.**
- **Scope:** upcoming, imported (`source != ""`) events whose kind is blank and not set by an admin.
- **Options:** `--dry-run`, `--limit`, `--model`.
- **Report:** counts per kind, and every event it would hide, by venue.
- **It reuses `classification.classify`.**

## Risks / Trade-offs

- **[A real show gets labelled non-music]** → It's hidden, not deleted, and the "all non-music" filter makes misses easy to scan. The admin relabel is permanent. Run the backfill's dry run first and check it against the examples in the proposal.
- **[Borderline kinds change their mind later]** → Kinds are stored, and only `MUSIC_KINDS` decides visibility, so including karaoke later is a one-line change, not a relabelling.
- **[Prompt drift between the two labelling paths]** → Both read their kind definitions from one constant, `classification.KIND_DEFINITIONS`.
- **[Cost]** → About $0.01 per 50 events with Haiku. The backfill of ~2,200 events is about 45 calls. Daily runs label only new events.

## Testing

- **Anthropic:** tests never call the API. Labelling is tested with a mocked client returning canned `labels` JSON. That covers batching (120 items make 3 calls), missing indexes, invalid kinds, a failed batch and the request's schema.
- **AI extraction:** tested through its existing mocked-client tests, with `kind` added.
- **`fetch_events` and `classify_events`:** tested with the classifier patched. The tests cover labelling only new events, admin labels sticking, unlabelled events when there's no key, and dry runs.
- **The admin's default filter and actions:** tested through the changelist.
- **The examples in the spec** (Jerry Garcia tribute, trivia, karaoke and so on) are prompt behavior, so they can't be asserted against a mock. A small `--live` eval script, `core/tests/evals/music_filter_eval.py`, run by hand and not in the suite, checks them against the real model. Its result is recorded in tasks.md.
