## 1. Name matching

- [ ] 1.1 Update `normalize_name` in `core/venue_matching.py`: strip accents, join apostrophes, drop a trailing parenthetical, expand st/ave/rd, and widen the noise words. Verify with unit tests in `core/tests/test_venue_matching.py` for every scenario in the spec, including the pairs that must still differ.
- [ ] 1.2 Run the existing Places, Ticketmaster and Eventbrite tests, and add a Places test that a name-matching result 40 km away still needs review. Verify that they all pass.

## 2. Check

- [ ] 2.1 Run the whole suite with outbound network blocked. Then run `lookup_venue_places --review --dry-run` locally (with approval for its ~180 Places searches) and record how many review venues would now be confident. Verify by hand that a sample of them are the right places.
