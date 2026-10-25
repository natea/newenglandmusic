# Design

## Context

See proposal.md. `Venue.latitude`/`longitude` come from the sheet and are overwritten on every sync. Today they're used by `Venue.google_maps_link`, the event page's map pin (`core/templates/core/event.html`), and the in-progress `match_ticketmaster_venues` command, which drafts `names_match` and `distance_km`. world-cup-watch-parties already calls the same API in `events/places.py`, using one isolated transport seam that its tests patch.

The relevant Places API (New) Text Search facts:
- The endpoint is `POST https://places.googleapis.com/v1/places:searchText`. The key goes in the `X-Goog-Api-Key` header and the fields to return in `X-Goog-FieldMask`.
- `pageSize` is 1–20.
- `locationBias.circle.radius` can be up to 50,000 m.
- Field tiers:
  - Pro: `displayName`, `formattedAddress`, `location`, `businessStatus`, `googleMapsUri`, `addressComponents`, `types`
  - Enterprise: `websiteUri`, `nationalPhoneNumber`
  - IDs Only: `id`

## Goals / Non-Goals

**Goals:**
- Exact, trustworthy locations for as many venues as possible, in one cheap run.
- Never let a wrong match move a venue.

**Non-Goals:**
- Writing results back to the sheet. This could be added later as an export.
- Venue photos, which world-cup-watch-parties does.
- Changing `is_active` from Google's status. The sheet owns that field.
- Scheduled refreshes.

## Decisions

**1. Store results in separate `place_*` fields on `Venue`, not a separate model.**
- **Fields:**
  - `place_id`, `place_name`, `place_address`
  - `place_latitude`, `place_longitude`
  - `place_business_status`, `place_maps_url`, `place_website`, `place_phone`
  - `place_lookup_status`: blank, `confident`, `review` or `not_found`
  - `place_looked_up_at`
- **Why:** one venue has at most one place, and admin editing stays simple. The sync only writes the fields it maps, which its `venue-sheet-sync` test already guards.
- **Alternative:** a `VenuePlace` one-to-one model. It's cleaner to drop later, but adds a join and an inline admin for no real gain now.

**2. Add `Venue.exact_location` (and `location_latitude`/`location_longitude`) as the single read path.**
- It returns the place coordinates when `place_lookup_status == "confident"`, and the sheet coordinates otherwise.
- `google_maps_link` returns `place_maps_url` when confident, and otherwise builds a link from the location as today.
- **Callers that switch to it:** the event template and `match_ticketmaster_venues`.
- **Why:** a single property keeps "only confident matches are used" in one place.

**3. Move name and distance matching into a shared module, `core/venue_matching.py`.**
- `normalize_name`, `names_match` and `distance_km` move there from the in-progress `match_ticketmaster_venues.py`, and both commands import them. Their tests move too.
- Google results have the same "presented by Citizens" naming quirks as Ticketmaster's.

**4. Accept a result as confident only when three checks pass:**
- the names match (the shared rule)
- the `administrative_area_level_1` short name from `addressComponents` equals the venue's state
- it lies within 25 km of the sheet coordinates, when there are any

**Why these thresholds:**
- 25 km covers a town-centre error, such as Warsaw in Brooklyn at 8 km, without accepting a same-named place in another town.
- The search text includes the town and state, and the location bias is a 30 km circle around the sheet coordinates, so the top result is usually the right one.
- Only the top 3 results are considered. The first that passes is taken, so a nearby but differently named result doesn't win.

**5. Keep the Places client as a small module with one transport seam, mirroring world-cup-watch-parties.**
- `core/places.py` exposes `search_place(text, bias_lat, bias_lng, contact=False)`, which returns a list of result dicts.
- It uses `requests`, to match the rest of this project, rather than urllib.
- It throttles to 5 requests per second and retries twice on 429 or 5xx.
- The field mask is built from the Pro fields, plus `websiteUri,nationalPhoneNumber` only with `--contact`, because Enterprise has 1,000 free calls a month against Pro's 5,000.
- The key is sent in a header, never in the URL, so no error or log line can contain it.

**6. Save results with `queryset.update()`, not `save()`, then re-render the stored event HTML of venues whose location changed.**
- `Venue.save()` would rebake every one of the venue's events.
- **Found during implementation:** each event's HTML, including its map pin and MAP link, is pre-rendered and stored on the event (`baked_html_template`). So when a lookup changes a venue's location or Maps link, its events must be rebaked, or the calendar keeps the old pin.
- The command rebakes only the events of venues whose location or Maps link actually changed, and skips this on a dry run.
- The admin actions call `save()`, which rebakes anyway.

**7. Report closed venues; don't deactivate them.** Permanently closed venues are listed so the people who edit the sheet can mark them inactive. The next sync then carries that through.

**8. Update the Ticketmaster change.** `match_ticketmaster_venues` uses `Venue.exact_location`. A venue without a confident lookup has only town-centre coordinates and will usually come out ambiguous, which is the safe outcome. The 1 km rule stays, as you decided.

## Risks / Trade-offs

- **[Google's top result is a different business at the same address]** → The name must match, and anything uncertain goes to review.
- **[Places terms restrict storing content other than place IDs]** → Fine for local use. Before going public, review the terms: possibly store only `place_id` and refresh the details, or attribute them. This is noted in the proposal.
- **[Cost creep from repeated runs]** → Venues already looked up are skipped. The default fields are Pro only. You were advised to cap the API's daily quota in Google Cloud.
- **[Sheet coordinates wrong by more than 25 km]** → Merriweather Post Pavilion is listed in Washington, DC but is in Columbia, MD. Its match goes to review, and the report surfaces it so the sheet can be fixed.

## Testing

- **Google Places:** tests never call Google. `core.places` is tested by mocking `requests.Session.post`. The command is tested with `core.places.search_place` patched, using a recorded response fixture with the key stripped (`core/tests/fixtures/places/`), captured once with a real key.
- **The template:** the event page's use of the exact location is tested by rendering the event page.

## Migration Plan

1. Apply the migration. The new fields start empty, and the site behaves exactly as before.
2. Add `GOOGLE_PLACES_API_KEY` to `.env`, restricted to the Places API (New).
3. Run `lookup_venue_places --limit 20 --dry-run`, review the matches, then run it for real over every venue. Settle any matches that need review in the admin.
4. Resume `add-ticketmaster-discovery-api` at task 3.3: re-run its matching dry run against the exact locations.

To roll back, reverse the migration. Nothing else depends on the new fields until step 4.

## Open Questions

**How should stored Places data change before any public deployment?** This doesn't affect local use or the tasks here. Google's Places policy lets place IDs be stored indefinitely and forbids storing other Places content beyond the allowed exceptions. As recalled, not yet confirmed: the Service Specific Terms allow caching latitude and longitude for up to 30 days. If that holds, a compliant version would:
- keep `place_id` permanently;
- re-fetch coordinates at least every 30 days, using `place_looked_up_at`, at about 730 Pro calls a month against 5,000 free;
- build the Maps link from the place ID (`https://www.google.com/maps/place/?q=place_id:<id>`) instead of storing `googleMapsUri`;
- take the street address from a source whose data may be stored, such as the US Census geocoder or OpenStreetMap;
- use business status, website and phone only in reports that sheet editors act on, never storing them.

A follow-up change should settle this against the current terms.
