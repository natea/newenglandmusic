## Why

178 venues are marked "Needs review" in the venue admin, and nothing says why. An admin has to open each one's Google Maps link and guess which check failed. The lookup knows exactly why when it decides: the name didn't match, the place is in another state, or it's too far from the sheet's town. It just doesn't keep the reason. Many review cases are near-misses that only need a click ("$3 Dewey's" against "Three Dollar Deweys"). Others are genuinely the wrong place, and the reason would tell them apart at a glance.

## What Changes

- **The lookup records why a match needs review:** which of its three checks failed ("name differs", "in another state", "too far"), and how far the place is from the venue's sheet coordinates, in km.
  - **Not Google's content:** these are our own judgments about the match. Google's name and address are still never stored.
  - **The distance expires with the coordinates:** it's worked out from Google's coordinates, so it's deleted when the 30-day rule deletes those.
- **The venue admin shows the reasons.** A "Why review" column, such as "name differs · 38 km away", and a filter by reason, so an admin can work through, say, all the "name differs" cases first. Marking a match confident, or clearing it, clears its reasons.
- **The admin shows Google's name for a review venue's place, live.** Google's terms don't let us store it, so the admin asks Google for it by place ID when it's needed, and keeps nothing:
  - on a review venue's page, when it opens;
  - in the list, only when the admin clicks "show Google's name" for one venue. Loading the list asks Google nothing.
  
  Each is one Place Details request for the name alone, inside the free 5,000 a month.
- **The existing review venues are re-checked once.** A new `--review` option re-runs the name search for venues already marked "Needs review", so they get their reasons. That's one Google Places search each, 178 locally, within the free 5,000 a month. The daily job is unchanged.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `venue-place-lookup`:
  - matches needing review record which checks failed and the distance;
  - the admin shows them and filters by them;
  - the stored fields include these judgments;
  - a `--review` option re-checks review venues;
  - the admin shows Google's name for a review venue's place, asked for live and never stored.

## Impact

- **Code:**
  - in `core/management/commands/lookup_venue_places.py`, `match_result` returns the failed checks, with a `--review` option;
  - `Venue.place_review_reasons` (an array of "name", "state", "distance") and `Venue.place_distance_km`, with a migration;
  - the venue admin's column and filter, and Google's name for a review venue (`PlacesClient.place_name`, a view for the list's click, and `core/static/core/admin/google-name.js`);
  - the 30-day expiry also clears `place_distance_km`.
- **Cost:** one-time, 178 Google Places Text Search requests, within the free tier. Run it only with the user's approval, after a `--dry-run`.
- **No change for visitors:** confident matches and the site's maps behave as before.
