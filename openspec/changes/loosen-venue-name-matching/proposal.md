## Why

Of the 176 venues whose Google Places match needs review, 172 failed only the name check (local run, 2026-10-29). Many of those are the right place, written slightly differently:
- "Fast Eddie's Billiards" against "Fast Eddies Billiards Cafe";
- "Shayna B's By The Sea" against "Shayna Bs By The Sea";
- "O'Brien's" against "O'Briens Pub";
- "Cultured Cafe" against "The Remedy's Cultured Café";
- "25 Central Street" against "25 Central St".

An admin has to confirm each by hand. The name check's normalizing is too literal: apostrophes split words ("eddie s" isn't "eddies"), accents aren't removed, common add-on words ("Cafe", "Pub", "Restaurant", "(Amesbury Location)") count as differences, and "St" isn't "Street". The same check also decides Ticketmaster and Eventbrite venue matches, which have the same problem.

## What Changes

- **The venue name check (`core.venue_matching.names_match`) compares names after:**
  - dropping apostrophes inside words ("Eddie's" becomes "eddies"), and accents ("Café" becomes "cafe");
  - dropping common add-on words when the rest still matches: cafe, pub, bar, restaurant, grill, tavern, lounge, bistro, brewery, taproom, as well as the noise words it already drops (the, club, hall, theatre, live…);
  - dropping a trailing parenthetical, such as "(Amesbury Location)";
  - treating "St" and "Street", "Ave" and "Avenue", "Rd" and "Road" as the same.
- **Unchanged:** the state and 25 km distance checks, which still have to pass. That's the safeguard against a looser name matching a different venue.
- **Applies to:** Google Places lookups, Ticketmaster venue linking and Eventbrite venue matching, which all use the same check. Their behavior only gets more lenient on these variations.
- **Clearing existing reviews:** after deploying, `lookup_venue_places --review` re-checks the review venues, and ones that now pass all three checks become confident (about 180 Places searches, inside the free tier).

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `venue-place-lookup`: adds how venue names are compared.

## Impact

- **Code:** `core/venue_matching.py` (`normalize_name`, `names_match`), with tests. No model, migration or dependency.
- **Risk:** a looser name check could match a different business at nearly the same name. The state and distance checks still apply, and Ticketmaster linking keeps its own 1 km limit and "same name preferred" rule.
- **Depends on** `explain-place-reviews` only for measuring: run `--review --dry-run` before and after, and compare the counts of name-only reviews.

- **Added after the first run (2026-10-29):** a name of only noise words must match exactly, and a place Google types only as a park, town or the like needs review, as "not a venue". See design.md's findings.
