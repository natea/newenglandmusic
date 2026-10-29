## Context

- **The match check:** `match_result()` in `lookup_venue_places` already applies three checks to each result: `names_match`, the same state, and within `MAX_DISTANCE_KM` (25) of the sheet's coordinates. It returns REVIEW with the top result when none passes all three. Only the status, place ID and coordinates are saved.
- **Google's terms (see `venue-place-lookup`):** only the place ID, and the coordinates for 30 days, may be stored. The 30-day expiry runs in every `lookup_venue_places` run.
- **The admin:** it already has the "place on Google Maps" link, the status filter, and the "mark confident" and "clear" actions.

## Goals / Non-Goals

**Goals:**
- Say which checks failed for every review venue, in the admin.

**Non-Goals:**
- Showing Google's name or address for the candidate. The terms forbid storing it, and the Maps link already shows it live.
- Auto-confirming near-misses. That's for an admin.

## Decisions

**1. The reasons are the top result's failed checks.**
- **What's recorded:** when no result passes all three checks, `match_result` returns the top result, as now, plus the checks it failed, in a fixed order (name, state, distance), and its distance rounded to 0.1 km.
- **Why the top result:** it's the one saved and linked, so the reasons describe what the admin will see behind the Maps link.
- **Storage:** `Venue.place_review_reasons` is an `ArrayField(CharField)`, as `GeoArea.states` already is. `Venue.place_distance_km` is a nullable float.

**2. The distance expires with the coordinates.** The distance comes from Google's coordinates, so the expiry step that nulls `place_latitude` and `place_longitude` after 30 days also nulls `place_distance_km`. The reasons are kept: they're true/false judgments with no Google content. A refresh by place ID doesn't recompute them; `--review` does.

**3. The admin.**
- **The column:** `why_review` joins the reasons in words, "name differs", "in another state", and "38 km away" (or the distance when only that failed), separated by " · ".
- **The filter:** `PlaceReviewReasonFilter` lists the three reasons, using `place_review_reasons__contains=[reason]`.
- **Clearing:** the "mark confident" and "clear" actions empty both fields.

**4. `--review` for the backfill.** It selects `place_lookup_status=REVIEW`, ignoring whether a venue was looked up before, and otherwise runs the plain search path. It's a one-off, run manually, not added to `bin/daily.sh`.

**How it's tested.** Nothing reaches the network.
- **Google Places:** `core/places.py` is already mocked in `core/tests/test_lookup_venue_places.py`, with a fake search returning hand-written results. The new tests reuse it for:
  - reasons recorded;
  - several reasons;
  - the distance expiring;
  - the backfill, and its dry run.
- **The admin:** admin tests for the "Why review" column, the reason filter, and the actions clearing the fields.

## Risks / Trade-offs

- **[Is a stored distance "Places content"?]** → It's computed by us, from Google's coordinates. To stay safe, it's deleted when the coordinates are, so it's never kept longer than they may be. The reasons themselves contain nothing from Google.
- **[Backfill cost]** → 178 searches, once, inside the free 5,000 a month. Run `--review --dry-run --limit 20` first, then the rest with approval.

## Migration Plan

1. Deploy the migration and code. Existing review venues have empty reasons until the backfill.
2. Run `lookup_venue_places --review` locally and on Render, with approval.
