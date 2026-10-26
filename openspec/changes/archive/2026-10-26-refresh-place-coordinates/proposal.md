## Why

The site is about to go public, and the Google Places data it keeps doesn't meet Google's terms. Google's Places policies say:
- place IDs may be stored indefinitely;
- latitude and longitude may be cached for up to 30 consecutive days;
- other Places content must not be pre-fetched, cached or stored "beyond the allowed exceptions".

Today `lookup_venue_places` stores each venue's coordinates with no expiry. It also stores the place's name, address, business status, Maps link, and optionally its website and phone. `PRODUCTION.md` lists this as one of the three blockers to running the jobs on a server. The user chose a monthly refresh to fix it.

## What Changes

- **Coordinates are refreshed by place ID.** `lookup_venue_places --refresh-stale` re-fetches the coordinates of every venue whose Places data is older than `--max-age-days`, which defaults to 25. It uses Place Details on the stored place ID rather than searching again, so a match an admin confirmed stays confirmed. It's meant to run daily with the other jobs, so each venue is refreshed about every 25 days.
- **Coordinates expire after 30 days.** Any stored Places coordinates older than 30 days are deleted at the end of every run, whether or not their refresh succeeded, and even when no requests can be made at all. The venue then falls back to the sheet's town-centre coordinates until a later refresh succeeds. The place ID and the match status are kept.
- **A place that's gone is looked up again.** If Place Details says a place ID no longer exists, the venue's lookup is cleared and reported. The next lookup run then searches for it by name, as for a new venue.
- **BREAKING: no other Places content is stored.**
  - `place_name`, `place_address`, `place_business_status`, `place_maps_url`, `place_website` and `place_phone` are removed from `Venue`.
  - These values are still used while a run is in progress: to judge a match (name, state, distance) and to report permanently closed venues. They're never saved.
  - `--contact` is removed, since website and phone would no longer be kept.
- **The MAP link is built from the place ID** with a Google Maps URL (`query_place_id`), instead of storing `googleMapsUri`.
- **Stored event HTML stays within the rules.** Each event's stored HTML includes its venue's coordinates for the day map. Whenever a refresh or expiry changes a venue's location, its events are re-rendered.
- **The venue admin** keeps the place ID, coordinates, match status and when they were fetched. A "View on Google Maps" link from the place ID replaces the stored name and address when reviewing a match, and the business-status filter goes away.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `venue-place-lookup`:
  - Coordinates are refreshed by place ID and expire after 30 days.
  - Only the place ID, coordinates, match status and fetch time are stored.
  - The MAP link comes from the place ID.
  - `--contact` and the business-status filter are removed.

## Impact

- **Model:** one migration removes six `place_*` fields from `Venue`. `place_looked_up_at` now means when the coordinates were last fetched.
- **Code:**
  - `core/places.py`: a `place_details(place_id)` request.
  - `lookup_venue_places`: `--refresh-stale`, `--max-age-days` and the expiry step. `--contact` is removed.
  - `Venue.google_maps_link` builds the link from the place ID.
  - `VenueAdmin`: fields, filter and the clear action.
- **Cost:** about 730 venues refreshed every 25 days is roughly 880 Place Details requests a month, plus a Text Search for each new venue. Requesting only `id`, `location` and `businessStatus` puts each request in the Place Details Pro SKU, with 5,000 free a month, so this stays inside the free allowance.
- **Not covered here:** Google's policy also says Places results "displayed on a map must be shown on a Google Map". The day maps are MapLibre with Protomaps tiles. See the design's open questions.
- **Docs:** `PRODUCTION.md`'s third blocker is resolved, and its schedule gains the daily `--refresh-stale` run.
