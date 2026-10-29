## Context

`core/venue_matching.py` holds `normalize_name` (lowercase, punctuation to spaces, a few noise words dropped via `NAME_NOISE_RE`) and `names_match` (equal, or one contained in the other as whole words). `lookup_venue_places`, `match_ticketmaster_venues` and Eventbrite's venue matching call `names_match`. The `explain-place-reviews` backfill (2026-10-29) showed 172 of 176 review venues failing on the name alone.

## Goals / Non-Goals

**Goals:** stop trivial spelling differences failing the name check, everywhere it's used.

**Non-Goals:** fuzzy or edit-distance matching ("Speedway" vs "Raceway"); changing the state, distance or Ticketmaster preference rules; auto-confirming venues an admin already reviewed.

## Decisions

**1. Normalize harder; keep "contained as whole words".** Steps, in order: Unicode NFKD and drop combining marks; lowercase; `&` to " and "; remove apostrophes (`'` and `’`) so "eddie's" becomes "eddies"; drop a trailing `( … )`; other punctuation to spaces; expand `st`/`ave`/`rd` to `street`/`avenue`/`road` as whole words; drop the noise words; collapse spaces; if nothing is left, fall back to the unstripped words (as now). Alternative rejected: a similarity score (e.g. `difflib` ratio), which is harder to reason about and would match "Speedway"/"Raceway".

**2. A wider noise list, applied to both names.** Adding cafe, pub, bar, restaurant, grill, tavern, lounge, bistro, brewery and taproom. Because both sides are stripped, "O'Brien's" and "O'Briens Pub" both become "obriens". The safety net is the other checks (state, 25 km, and for Ticketmaster 1 km and the same-name preference), which this change doesn't touch.

**3. One function, all callers.** The change stays in `normalize_name`, so Places, Ticketmaster and Eventbrite all benefit, and their existing tests keep guarding their own rules.

**How it's tested.** Pure-function unit tests in `core/tests/test_venue_matching.py` for every scenario, plus the existing Places, Ticketmaster and Eventbrite tests (all mocked; nothing reaches the network) still passing.

## Risks / Trade-offs

- **[A looser match picks a different business nearby]** → It still has to be in the state and within 25 km (Places) or 1 km (Ticketmaster); and "bar"/"pub" are only dropped as whole words, so "Barcade" stays "barcade".
- **[Existing confident or linked venues change]** → Matching only becomes more lenient, so nothing confident becomes unmatched; Ticketmaster's preference for an exact-name candidate still picks the same one.

## Migration Plan

Deploy, then run `lookup_venue_places --review --dry-run` to see how many reviews would clear, then without `--dry-run` (about 180 Places searches, with approval), locally and on Render.
