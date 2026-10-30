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

## Findings from the first run (2026-10-29)

`lookup_venue_places --review`, run locally against the 176 review venues (the before and after are in `logs/place-status-2026-10-29-loosen-comparison.csv`), made 41 confident. 35 were right, such as "Night Shift Brewery" to "Night Shift Brewing - Everett", "Cafe 641" to "Café 641", and "Hillside Johnny's" to "Hillside Johnnys". Six were wrong or doubtful, and were put back to review by hand:

- **Wrong, because dropping a noise word left a place name:** "Spicket River Brewery" matched "Spicket River Greenway", a park.
- **Wrong, because a name of only noise words was contained:** "The Music Hall" (Portsmouth) matched "The Music Hall Lounge", its separate small venue. Before this change "lounge" wasn't a noise word, so the two didn't match.
- **Doubtful:** "The Brick House" to "The Brick Bar & Grill", "Union Square Tavern" to "Union Tavern", "The Walnut Street Cafe" to "Walnut Street Coffee Cafe", and "Bent Nails Bistro" to "Bent Nails Roadhouse" (9.4 km).

This contradicts the risk analysis above, which relied on the state and distance checks: all six are within 10 km. Two fixes, both built (task 2.2):

1. **A name of only noise words must match exactly.** When normalizing leaves nothing and the whole name is used, require the two names to be equal rather than one contained in the other. That fixes The Music Hall. A leading "the" is ignored, so "The Music Hall" still matches "Music Hall".
2. **Reject places that aren't venues.** Ask Places for `places.types` (part of the same Pro field set, so no extra cost) and send a result typed as a park, natural feature or locality to review. That fixes Spicket River. A place also typed as a venue ("event_venue" with "park", for an amphitheatre in a park) still counts, and so does one with no types. The types are used during the run and never stored, and the failed check is recorded as the reason "type" ("not a venue" in the admin).

The doubtful four need an admin's judgment either way. The 135 still in review are mostly festivals and Porchfests mapped to a town or park, which are right to stay in review, plus run-together words that this change doesn't handle ("Kung Fu Neck Tie" vs "Kung Fu Necktie", "No Fun" vs "NoFun", "Game Time" vs "Gametime Lanes").

### Checking the two fixes against Google (2026-10-29)

A dry run of the 41 loosened matches with the fixes, against live results, needed two adjustments:

- **Google adds the town to some names.** For Portsmouth's music hall it returned "The Music Hall, Portsmouth, NH", the main hall at 28 Chestnut St, which an exact match rejected. A name of only noise words now matches when the other name's extra words are only the venue's town and state (`names_match(..., place_words=...)`, which the Places lookup passes and Ticketmaster and Eventbrite don't). It still rejects "The Music Hall Lounge".
- **Google typed the Spicket River Greenway `hiking_area` and `sports_activity_location`**, not `park`. `sports_activity_location` is a parent type a stadium has too, so it now says nothing either way, like `point_of_interest`; a stadium still counts by its own `stadium` type.

With both, the dry run made The Music Hall confident on the right place and sent Spicket River Brewery to review as "not a venue". Google's top result for that search is "Rapscallion Brick Oven Pizza and Brewery", a live-music brewpub, which may be the venue the sheet means. The other 39 matches stayed confident, including the four doubtful ones, which pass both fixes and need an admin. Three of the 41 are permanently closed on Google: Cultured Cafe (V0034), Shayna B's By The Sea (V0067) and Farmer's Table Cafe (V0482).
