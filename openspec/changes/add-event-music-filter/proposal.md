# Proposal

## Why

Imported events include many that aren't music performances: trivia, comedy, karaoke, classes, markets, screenings, holiday parties and craft nights. A keyword scan of the ~2,200 upcoming events suggests about 28% of iCal events are non-music, along with 10–12% of JSON-LD, ticketing-page and AI-extracted events. Even Ticketmaster's "Music" category lets some parties through. A keyword filter can't fix this. It flags real shows such as "A Very Jerry Halloween with Rose Alley (Jerry Garcia Band Tribute)" and "Brass Against – Halloween Tour", and it misses non-music events whose titles contain no keyword. Telling them apart needs judgment about what's being billed.

## What Changes

- **Every imported event gets a kind:**
  - `live_music`: bands, solo artists, tribute acts
  - `dj_dance`: DJ sets, dance nights
  - `open_mic`: music open mics and jams
  - `karaoke`
  - `comedy`
  - `other`: trivia, classes, markets, screenings, games, parties with no billed band or DJ

  The first three count as music. A themed party (Halloween, holiday) counts as music only when a band or DJ is billed.
- **How events are labelled:**
  - AI-extracted events get their kind in the same extraction call.
  - Events from iCal, JSON-LD, ticketing pages and Ticketmaster are labelled by Claude Haiku in batches of up to 50.
  - An admin's label is never overwritten by a later import.
- **Non-music events are kept, hidden.** They're saved with their kind and left out of the review queue by default, so a mislabelled show is never lost and an admin can relabel it.
- **Admin:**
  - A "Kind" column and filter on the events list.
  - The list defaults to music events.
  - Admin actions to relabel events.
- **New `classify_events` command:** labels events that are already in the database, for a one-time backfill of the ~2,200 upcoming events. It supports `--dry-run`, which lists what would be hidden, before anything changes.
- **Without `ANTHROPIC_API_KEY`:** events are saved unlabelled and still appear in the review queue, so nothing is hidden without a decision.

## Capabilities

### New Capabilities

- `event-music-filter`: labels each imported event with what kind of event it is, and keeps non-music events out of the review queue.

### Modified Capabilities

- `ai-event-extraction`: extracted events also carry their kind, so AI-extracted events need no separate labelling call.

## Impact

- **Model:** `Event` gets `kind` and `kind_set_by` (`ai` or `admin`), in one migration.
- **New code:** `core/event_fetching/classification.py`, which labels events in batches, and the `classify_events` management command.
- **Changed code:**
  - `ai_extraction.py`: the schema and prompt get the kind.
  - `fetch_events`: labels events before saving them.
  - `EventAdmin`: the Kind column, the default-to-music filter and the relabel actions.
- **Cost:** Haiku, about 50 events per call. The backfill is about 45 calls, well under $1. Each later run labels only new events.
- **Not breaking:** existing approvals are untouched. An approved event that's later labelled non-music stays approved and stays on the site.
