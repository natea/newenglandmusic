## Context

- **The lookup today:** `lookup_venue_places` runs a Places Text Search for each venue and stores eight `place_*` fields: ID, name, address, coordinates, business status and Maps link, plus website and phone with `--contact`. It also stores the match status and `place_looked_up_at`.
- **What the public site uses:** only the coordinates and the Maps link, both through `Venue.exact_location` and `Venue.google_maps_link`. They appear in `event.html`, whose output is stored per event (`baked_html_template`), and in Ticketmaster venue matching. Name, address, business status, website and phone are only shown in the venue admin, to help judge a match.
- **What the terms allow:** Google's Places policies say the place ID "is exempt from the caching restrictions… You can therefore store place ID values indefinitely", and "You must not pre-fetch, cache, or store Places API content beyond the allowed exceptions". The Service Specific Terms make the other exception: latitude and longitude may be cached for up to 30 consecutive days. The archived `add-venue-place-lookup` design left this as an open question for a follow-up change, and this is that change.
- **Venues:** 729, most with a place ID.

## Goals / Non-Goals

**Goals:**
- Store only what the terms allow: the place ID indefinitely, coordinates for at most 30 days.
- Keep the site's locations exact without manual work, and inside the free Places allowance.

**Non-Goals:**
- **Map tiles:** the policy's "results displayed on a map must be shown on a Google Map" rule. See Open Questions.
- **Street addresses from another source** (Census, OpenStreetMap): nothing public shows an address today.
- **Refreshing contact details:** website and phone are dropped, not refreshed.

## Decisions

### Refresh with Place Details on the stored ID, not a new Text Search

`PlacesClient.place_details(place_id)` sends `GET https://places.googleapis.com/v1/places/{id}`, with the key in `X-Goog-Api-Key` and `X-Goog-FieldMask: id,location,businessStatus`.

Why Place Details rather than a new name search:
- **It's exact:** it can't land on a different place.
- **It keeps admin decisions:** a match an admin marked confident stays confident.
- **It's cheaper:** about 880 Place Details Pro requests a month fit the 5,000 free, and it uses fewer billable fields than a Text Search.

`businessStatus` makes it the Pro SKU rather than Essentials, but it keeps the monthly closed-venue report, which sheet editors act on. Leaving it out would save nothing that matters at this volume.

*Alternative: re-run the Text Search.* Rejected: it re-matches and can overturn an admin's decision. The existing `--refresh` still does a full re-search, for when that's wanted.

### Refresh at 25 days, delete at 30, in every run

- `--refresh-stale` selects venues with a place ID and a `place_looked_up_at` older than `--max-age-days`, which defaults to 25.
- The daily job then refreshes about 1/25th of the venues each day, so there's no monthly burst.
- The five days between 25 and 30 cover a few failed daily runs.
- `expire_stale_coordinates()` runs at the end of every invocation, in a `finally` block, so a crash or a Places outage doesn't skip it. It also runs before the missing-key error. It sets `place_latitude` and `place_longitude` to null for venues fetched more than 30 days ago (a constant, `COORDINATE_MAX_AGE_DAYS = 30`), keeping `place_id` and `place_lookup_status`.
- `exact_location` already falls back to the sheet coordinates when the place coordinates are null, so the site needs no change.

`place_looked_up_at` now means "coordinates last fetched". Text Search and Place Details both set it. Marking a match confident in the admin fetches nothing, so it doesn't change it.

*Alternative: a separate expiry command.* Rejected: a second scheduled job is one more thing that can silently stop. Putting expiry in the lookup's `finally` ties it to the job that has to run anyway.

### Errors and missing places

- **404 / `NOT_FOUND`:** the ID is obsolete or the place was removed. Clear the lookup, the same as the admin action: place ID, coordinates, status and fetch time. Report it. The next plain run searches for the venue by name and may land on review again.
- **Retried failures** (network errors, 429, 5xx) **and other 4xx responses:** report the venue as failed and keep its data. Expiry then decides: coordinates are kept until day 30 and deleted after it.
- **A different `id` in the response** (Google moved the place): store the new ID.

`PlacesClient` gains a `PlaceNotFound(PlacesError)` exception for 404, so the command can tell it apart from other failures.

### Remove the other content fields

The migration drops `place_name`, `place_address`, `place_business_status`, `place_maps_url`, `place_website` and `place_phone`.
- **During a run:** `match_result` still reads name, state and location from the in-memory search result, and the closed-venue report reads `business_status` from it.
- **Admin:** it shows a "View on Google Maps" link from the place ID in place of the stored name and address, and loses the business-status filter.
- **`--contact`** and `CONTACT_FIELDS` are removed.

`Venue.google_maps_link` becomes `https://www.google.com/maps/search/?api=1&query=<lat>,<lng>&query_place_id=<id>` for a confident match, Google's documented Maps URLs form, and stays the coordinate search otherwise. It needs no stored Places content beyond the ID and coordinates.

*Alternative: keep the fields but refresh them monthly too.* Rejected: the terms allow caching only coordinates, not other content, however fresh.

### Save without re-rendering, then re-render only what changed

Venues are saved with `Venue.objects.filter(pk=…).update(…)`, as today, because `Venue.save()` re-renders every event of the venue. The existing logic runs after each refresh, expiry or clear: compare `(exact_location, google_maps_link)` before and after, and call `rebake_events(venue)` only when they differ.
- **A refresh** that returns the same coordinates re-renders nothing, which will be almost every one.
- **An expiry** always changes the location, so it always re-renders. That's required: the stored HTML holds the coordinates in `data-venue-lnglat`, so it's a cache of Places content too.

### Testing

No test touches the network:
- **Places:** `PlacesClient` tests use a fake session, as `test_places.py` does now. A Place Details response is recorded once into `core/tests/fixtures/places/details_paradise.json`, with the key stripped. That's a single real request, well inside the free tier.
- **Command tests:** they mock `PlacesClient`, as `test_lookup_venue_places.py` does, and control time with `django.utils.timezone.now` patched, so "26 days old" and "31 days old" are exact.
- **Other services:** none are involved.

## Risks / Trade-offs

- **[Admins lose the stored name and address when judging a match]** → The Maps link by place ID shows the live place, which is more accurate anyway.
- **[A long Places outage]** → After day 30, pins fall back to town centres. The site degrades but stays within the rules.
- **[Every venue looked up today has no fetch time older than this change]** → On the first `--refresh-stale` run, any venue looked up more than 25 days ago is refreshed at once: up to ~730 requests, still free. `place_looked_up_at` is already set for every looked-up venue, so no backfill is needed.
- **[Restoring the local database into production]** → Coordinates keep their fetch times, so expiry applies to them as normal.

## Migration Plan

1. Deploy the migration and code.
2. Run `lookup_venue_places --refresh-stale --dry-run`, then a real run.
3. Add `--refresh-stale` to the daily job in `PRODUCTION.md`.

Rollback: revert. The dropped fields would be empty, and a `--refresh` run refills everything except contact details.

## Open Questions

- **Map tiles:** the Places policy says Places "results displayed on a map must be shown on a Google Map", and that showing Places data without a Google Map needs the Google logo. The day maps place pins at Places coordinates on MapLibre with Protomaps tiles. This change doesn't settle that. The options are:
  1. Switch the day maps to the Google Maps JavaScript API, which has its own cost.
  2. Pin venues from a geocoder whose results may be stored (US Census or OpenStreetMap), and use Places only for matching and the MAP link.
  3. Get a reading of the terms that allows the current maps.

  The user should choose before launch. It's a separate change either way, and it doesn't change this one's tasks.
- **Pricing:** confirm the Place Details Pro free allowance (5,000 a month) on Google's current pricing page before the first real run. If it has changed, `--max-age-days` can stretch toward 28 to reduce calls.
