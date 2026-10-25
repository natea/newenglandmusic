# Tasks

## 1. Model, location and admin

- [ ] 1.1 Add the `place_*` fields and `place_lookup_status` choices to `Venue` (design decision 1), with a migration; verify that it applies and reverses cleanly
- [ ] 1.2 Add `Venue.exact_location` and make `google_maps_link` prefer `place_maps_url` for confident matches; add tests in `test_venue_model.py` for confident, review-needed and not-looked-up venues, and verify that they pass
- [ ] 1.3 Use the exact location for the event page's map pin (`event.html`); add a test that renders an event page for a confident venue and for a review-needed venue and checks `data-venue-lnglat` and the MAP link, and verify that it passes
- [ ] 1.4 Add a "Place" fieldset, filters for lookup status and business status, and "Mark place match as confident" and "Clear place lookup" actions to `VenueAdmin`; add tests for the filters and both actions in `test_venue_admin.py`, and verify that they pass
- [ ] 1.5 Add a test to `test_sync_venues_from_gsheets.py` that a sync leaves the `place_*` fields unchanged, and verify that it passes
- [ ] 1.6 Add `GOOGLE_PLACES_API_KEY=''` to `.env.example`, with a note to restrict the key to the Places API (New); verify `.env` is still git-ignored

## 2. Shared matching and the Places client

- [ ] 2.1 Move `normalize_name`, `names_match` and `distance_km` into `core/venue_matching.py` and import them in `match_ticketmaster_venues`; move their tests to `core/tests/test_venue_matching.py`, and verify that the suite still passes
- [ ] 2.2 Create `core/places.py` with `search_place(text, bias_lat, bias_lng, contact=False)`: the key sent in a header, a Pro-only field mask unless `contact`, `pageSize` 3, a 30 km location bias when there are coordinates, a ≥0.2s throttle, and 2 retries on 429/5xx. Add `core/tests/test_places.py` with a mocked `requests.Session`, covering the request body and headers, the field mask with and without `contact`, no bias without coordinates, retry then success, repeated failure, and errors that never contain the key. Verify that the tests pass
- [ ] 2.3 With a real key, look up three venues (Paradise Rock Club, MA; Aura, ME; Merriweather Post Pavilion, DC) and save the responses with the key stripped under `core/tests/fixtures/places/`; verify that the fixtures contain no key

## 3. Lookup command

- [ ] 3.1 Add `lookup_venue_places` with `--sheet-ids`, `--state`, `--limit`, `--refresh`, `--contact` and `--dry-run`, and a clear error without `GOOGLE_PLACES_API_KEY`; skip looked-up venues unless `--refresh`; save with `update()`. Verify with tests for the missing-key error, skipping, refresh and dry run
- [ ] 3.2 Implement the confident-match rule (design decision 4: top 3 results, name, state from `addressComponents`, 25 km) and the not-found case; verify with fixture-based tests that Paradise is confident, Merriweather (wrong sheet town) needs review, a different-name result needs review, an out-of-state result needs review, no results is not found, and `is_active` and the sheet fields are never changed
- [ ] 3.3 Report the groups: confident, needs review (with name, address and distance), not found, permanently closed, and failed. Verify with a test that a failed request for one venue is reported, leaves that venue's data unchanged and doesn't stop the run, and that the output never contains the key
- [ ] 3.4 Document the command's usage and cost in its module docstring, matching the style of `fetch_events`

## 4. Run it, then hand back to Ticketmaster

- [ ] 4.1 Run `lookup_venue_places --limit 20 --dry-run` and review the matches, then run it for all active venues; settle review-needed matches in the admin; record how many venues are confident, need review, aren't found or are closed
- [ ] 4.2 In the `add-ticketmaster-discovery-api` change, make `match_ticketmaster_venues` use `Venue.exact_location`, with a test that a review-needed venue's place coordinates are not used. Verify the full suite passes with outbound network blocked
- [ ] 4.3 Re-run `match_ticketmaster_venues --dry-run` and record how many of the 23 venues now link; continue that change from its task 3.3

## Workflow follow-up

- Review the Google Maps Platform terms on storing Places content before any public deployment.
- Archive this change after its tests pass and the runs above are recorded.
