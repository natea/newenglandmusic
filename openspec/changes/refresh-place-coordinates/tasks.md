## 1. Place Details client

- [ ] 1.1 Add `PlacesClient.place_details(place_id)` to `core/places.py`. It sends `GET /v1/places/{id}` with the key in `X-Goog-Api-Key` and the field mask `id,location,businessStatus`, uses the existing throttle and retries, and returns `{id, latitude, longitude, business_status}`. Add `PlaceNotFound(PlacesError)` for 404. Remove `CONTACT_FIELDS`, and the name, address, Maps URL, website and phone from `to_place_dict`'s saved use (keep what matching and reporting need). Verify with the tests in 1.3.
- [ ] 1.2 Record one Place Details response for Paradise Rock Club into `core/tests/fixtures/places/details_paradise.json`, with the key stripped. This is one real request, inside the free tier. Verify that the fixture has no key and parses.
- [ ] 1.3 Extend `core/tests/test_places.py` with a fake session, verified when the tests pass. Cover: the request URL and field mask (only `id,location,businessStatus`); the recorded result; a 404 raising `PlaceNotFound` without retrying; retries on 429 and 5xx; the key never in an error message.

## 2. Store only the place ID and coordinates

- [ ] 2.1 Write a migration that removes `place_name`, `place_address`, `place_business_status`, `place_maps_url`, `place_website` and `place_phone` from `Venue`. Update the field comments, saying `place_looked_up_at` is when the coordinates were last fetched. Verify that `makemigrations --check` is clean after `migrate`.
- [ ] 2.2 Make `Venue.google_maps_link` build `https://www.google.com/maps/search/?api=1&query=<lat>,<lng>&query_place_id=<id>` for a confident match, and keep the coordinate link otherwise. Change `place_fields` in `lookup_venue_places` to save only ID, coordinates, status and fetch time. Remove `--contact`. Verify with the tests in 2.4.
- [ ] 2.3 Update `VenueAdmin`: remove the dropped fields and the business-status filter, add a read-only "View on Google Maps" link from the place ID, and update `clear_place_lookup`. Verify in the admin that a venue's Places section shows the ID, coordinates, fetch time and link.
- [ ] 2.4 Update `core/tests/test_lookup_venue_places.py`, `test_event_venue_map.py` and `test_venue_admin.py`, verified when they pass. Cover the scenarios "Confident match is stored", "No other content in the database", the modified "Confident match", "Closed venue", "Looked-up venue" (the MAP link uses `query_place_id`), "Match needing review", "Confirming a match" and "Clearing a lookup". Replace the old `--contact` test with the modified "Contact details requested" scenario.

## 3. Refresh and expiry

- [ ] 3.1 Add `--refresh-stale` and `--max-age-days` (default 25) to `lookup_venue_places`. They select venues with a place ID whose `place_looked_up_at` is older than the cutoff, call `place_details`, and store the new coordinates, the new ID if it changed, and the fetch time, keeping the match status. `PlaceNotFound` clears the lookup and reports it. Other errors report the venue as failed. Closed places are reported, not stored. Verify with the tests in 3.4.
- [ ] 3.2 Add `expire_stale_coordinates()`: it nulls the place coordinates of venues fetched more than `COORDINATE_MAX_AGE_DAYS = 30` days ago, keeps the ID and status, and reports the count. Run it in a `finally` block at the end of every invocation and before the missing-key error. It isn't run on `--dry-run`, where it only reports what would expire. Verify with the tests in 3.4.
- [ ] 3.3 After each refresh, expiry or clear, compare `(exact_location, google_maps_link)` before and after, and call `rebake_events` only when they differ. Save with `queryset.update()`. Verify with the tests in 3.4.
- [ ] 3.4 Write tests in `core/tests/test_lookup_venue_places.py`, with `PlacesClient` mocked and `timezone.now` patched, verified when they pass. Cover every scenario of:
  - "Stale coordinates are refreshed by place ID": stale coordinates, fresh coordinates, confirmed match survives a refresh, place ID changed, closed venue found while refreshing.
  - "Stored coordinates expire after 30 days": refresh fails past the limit, refresh fails within the limit, missing API key, expired coordinates restored.
  - "A place that no longer exists is looked up again": place gone.
  - "Stored event HTML follows the venue's location": coordinates expire (the stored HTML no longer holds them), refresh returns the same place (no re-render).
  - The modified "Dry run" and "Second run" scenarios.
- [ ] 3.5 Update the command's module docstring with the new options, the 25- and 30-day rules and the cost. Verify by reading it.

## 4. Docs and a real run

- [ ] 4.1 Update `PRODUCTION.md`: mark the Places blocker resolved, add `lookup_venue_places --refresh-stale` to the daily schedule with its cost (about 880 Place Details Pro requests a month), and note the map-tiles open question from design.md. Update the `venue-place-lookup` main spec's Purpose at archive, which still mentions address and status. Verify by reading both.
- [ ] 4.2 Confirm the Place Details Pro free allowance on Google's current pricing page, and record it in design.md.
- [ ] 4.3 Run the full test suite with outbound network blocked, and verify that it passes.
- [ ] 4.4 Run `lookup_venue_places --refresh-stale --dry-run`, logged to `logs/lookup_venue_places.log` with a dated header, and check the counts to refresh and to expire. Then ask the user before the real run.
