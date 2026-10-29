## 1. Recording the reasons

- [x] 1.1 Add `place_review_reasons` (an array of "name", "state", "distance") and `place_distance_km` to `Venue`, with a migration. Verify that `makemigrations --check` is clean.
- [x] 1.2 Make `match_result` return the top result's failed checks and its distance. Save them for review matches, and clear them for confident and not-found ones. Clear the distance in the 30-day expiry. Verify with tests for:
  - reasons recorded;
  - several reasons;
  - wrong place;
  - confident match with no reasons;
  - the distance expiring with the coordinates;
  - no other content in the database.

## 2. Backfill option

- [x] 2.1 Add `--review` to `lookup_venue_places`, to re-run the name search for review venues only, with `--limit`, `--state` and `--dry-run`. Verify with tests for backfilling the reasons and the dry run.

## 3. Admin

- [x] 3.1 Add the "Why review" column and the reason filter to the venue admin, and clear the fields in the "mark confident" and "clear" actions. Verify with admin tests for why a venue needs review, filtering by reason, and the actions clearing the reasons.

## 4. Docs and check

- [x] 4.1 Document `--review` and the reasons in PRODUCTION.md's Google Places section. Run the whole suite with outbound network blocked, then run `lookup_venue_places --review --dry-run --limit 20` locally, which spends 20 Places requests, after asking. Verify that the tests pass, and that the printed reasons match what the Maps links show.
