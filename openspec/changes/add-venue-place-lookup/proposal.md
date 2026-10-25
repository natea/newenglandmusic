# Proposal

## Why

The sheet's coordinates are town centres, not venue locations. 537 of 729 venues share their coordinates with another venue, and all 46 Portland, ME venues share one point. This breaks anything that needs to know where a venue actually is:
- **Ticketmaster matching.** The `add-ticketmaster-discovery-api` dry run linked only 3 of 23 venues, because correct listings sit 1–5 km from the town centre.
- **Event pages.** Each event's map pin and "MAP" link point at the middle of town.

The sheet also has no street addresses, and nothing tells us when a venue has closed. Google's Places API (the one world-cup-watch-parties uses) returns a venue's address, exact location, open/closed status and Maps link from its name and town.

## What Changes

- **New venue fields, held only in the database.** The sheet sync never touches them:
  - Google place ID, place name and address
  - exact latitude and longitude
  - business status (operational, closed temporarily, closed permanently)
  - Google Maps link
  - optionally, website and phone
  - when the venue was looked up, and whether the match was confident or needs review
- **New `lookup_venue_places` command:**
  - It searches Google Places for each venue by name, town and state, biased to the venue's town.
  - It saves the result as confident only when the name matches and the place is in the venue's state, near its town. Anything else is saved for review but not used.
  - It skips venues already looked up unless asked to refresh, supports a dry run, and reports permanently closed venues so the sheet can be updated.
- **Use exact locations where known.** Wherever the site uses a venue's location, it uses the confident looked-up one when there is one, and the sheet's otherwise. That covers the event map and "MAP" link, and Ticketmaster matching.
- **Admin:**
  - The new fields appear in a "Place" section.
  - New filters for lookup status and business status.
  - Admins can confirm a match that needs review, or clear a lookup.
- **Configuration:** `GOOGLE_PLACES_API_KEY` is read from `.env`. Without it, the command stops with a clear error. Nothing else depends on the key.
- **Not breaking:** venues that haven't been looked up behave exactly as they do today.

## Capabilities

### New Capabilities

- `venue-place-lookup`: looks up each venue on Google Places and stores its exact location, address, status and links, separate from the sheet's data, with uncertain matches held for review.

### Modified Capabilities

None among the archived specs. The in-progress `add-ticketmaster-discovery-api` change is updated so its matching uses these exact locations. Its 1 km rule stays.

## Impact

- **Model:** `Venue` gets the new fields, in one migration. `Venue.google_maps_link` and the event page's map use the looked-up location when it's confident.
- **New code:**
  - `core/places.py`, a client for the Places API (New) Text Search
  - `core/management/commands/lookup_venue_places.py`
- **Admin:** `VenueAdmin` gets the new fieldset and filters.
- **Configuration:** `GOOGLE_PLACES_API_KEY`, restricted in Google Cloud to the Places API (New).
- **External:**
  - Text Search Pro fields (address, location, status, Maps link) cost $32 per 1,000 calls, after 5,000 free calls a month.
  - The optional website and phone fields are Enterprise tier: $35 per 1,000 calls, after 1,000 free a month.
  - So one run over ~730 venues fits in the free allowances.
  - Google's Places terms limit storing Places content other than place IDs. These must be reviewed before any public deployment, and may require refreshing or attributing stored data. The project is local only for now.
