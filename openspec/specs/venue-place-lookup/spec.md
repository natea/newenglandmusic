# venue-place-lookup Specification

## Purpose
Finds each venue on Google Places and records its exact location, address, open/closed status and links, kept apart from the sheet's town-level data, so the site and venue matching can rely on where a venue really is.

## Requirements

### Requirement: Venues are looked up by name and town
The lookup SHALL search Google Places for each venue by name, town and state, biased to the venue's sheet coordinates when it has them, and SHALL consider only the top results.

#### Scenario: Venue found
- **WHEN** the lookup runs for "Paradise Rock Club" in Allston, MA
- **THEN** the search text includes the venue's name, town and state, and the request is biased toward the venue's sheet coordinates

### Requirement: Only confident matches are used
A result SHALL be stored as confident only when its name matches the venue's name, its address is in the venue's state, and it lies within 25 km of the venue's sheet coordinates (or the venue has none). Any other result SHALL be stored as needing review, with the reasons: each check it failed, as "name" (the name doesn't match), "state" (it's in another state) or "distance" (it's more than 25 km away), and its distance from the venue's sheet coordinates in km, to one decimal place, when both have coordinates. A confident or not-found venue SHALL have no reasons and no distance.

#### Scenario: Confident match
- **WHEN** the top result is "Paradise Rock Club presented by Citizens" at 967 Commonwealth Ave, Boston, MA, 1 km from the sheet's coordinates
- **THEN** its place ID and coordinates are saved and the match is marked confident

#### Scenario: Wrong place
- **WHEN** the top result has a different name, is in another state, or is more than 25 km away
- **THEN** it is saved as needing review, with each failed check as a reason, and its coordinates are not used anywhere

#### Scenario: Reasons recorded
- **WHEN** the top result for "$3 Dewey's" in Portland, ME has a different name, is in Maine, and is 0.4 km from the sheet's coordinates
- **THEN** it's saved as needing review with the reason "name" and the distance 0.4 km

#### Scenario: Several reasons
- **WHEN** the top result has a different name and is 38 km away in another state
- **THEN** its reasons are "name", "state" and "distance", and its distance is 38.0 km

#### Scenario: Nothing found
- **WHEN** the search returns no places
- **THEN** the venue is marked as not found and nothing else changes

### Requirement: Looked-up data is kept separate from the sheet
The looked-up fields SHALL be stored only in the database. The sheet sync SHALL NOT change them, and the lookup SHALL NOT change any field that comes from the sheet, including `is_active`.

#### Scenario: Sheet sync after a lookup
- **WHEN** venues are synced from the sheet after being looked up
- **THEN** their looked-up fields are unchanged

#### Scenario: Closed venue
- **WHEN** Google reports a venue as permanently closed
- **THEN** the venue's `is_active` is unchanged, the business status is not stored, and the lookup lists it as closed so the sheet can be updated

### Requirement: Exact locations are used where known
A venue's location SHALL be its confident looked-up coordinates when present, and its sheet coordinates otherwise. This location SHALL be used for its map pin, its "MAP" link and Ticketmaster venue matching. When there is a confident match, the "MAP" link SHALL be a Google Maps link built from the place ID.

#### Scenario: Looked-up venue
- **WHEN** an event's venue has a confident looked-up location
- **THEN** the event page's map pin uses that location, and its MAP link opens the place on Google Maps by its place ID

#### Scenario: Match needing review
- **WHEN** a venue's lookup needs review
- **THEN** its sheet coordinates are used, as before the lookup

### Requirement: Lookups are repeatable and cheap
The lookup SHALL skip venues already looked up unless told to refresh. It SHALL accept venue sheet IDs, a state filter and a limit, and SHALL support a dry run that saves nothing, not even an expiry. It SHALL request only the fields it needs: the Pro-tier fields for a name search, and only ID, location and business status for a refresh.

#### Scenario: Second run
- **WHEN** the lookup runs twice
- **THEN** the second run makes no requests for venues looked up by the first

#### Scenario: Dry run
- **WHEN** the lookup runs with `--dry-run`, with or without `--refresh-stale`
- **THEN** it reports what it found, what it would refresh and what would expire, and saves nothing

#### Scenario: Contact details requested
- **WHEN** the lookup runs, by name search or by refresh
- **THEN** the place's website and phone are never requested or saved, and there is no option to request them

### Requirement: Admins can settle uncertain matches
The venue admin SHALL show the place ID, the looked-up coordinates, when they were fetched and a Google Maps link from the place ID. It SHALL filter by lookup status, and SHALL let an admin mark a match needing review as confident, or clear a venue's lookup. For a match needing review, the list SHALL show a "Why review" column naming its reasons in words ("name differs", "in another state", "38 km away"), and SHALL filter by each reason. For a match needing review, the admin SHALL also show the place's name on Google, asked for by its place ID when needed and never stored: on the venue's page when it opens, and in the list only when the admin asks for that venue. Loading the list SHALL NOT ask Google for anything. Marking a match confident, or clearing a lookup, SHALL clear its reasons and distance.

#### Scenario: Confirming a match
- **WHEN** an admin marks a venue's review-needed match as confident
- **THEN** its looked-up location is used from then on

#### Scenario: Clearing a lookup
- **WHEN** an admin clears a venue's lookup
- **THEN** its looked-up fields are emptied and the next lookup run searches for it again

#### Scenario: Why a venue needs review
- **WHEN** an admin opens the venue list filtered to "Needs review"
- **THEN** each venue shows why, such as "name differs · 0.4 km away" for $3 Dewey's

#### Scenario: Google's name on the venue page
- **WHEN** an admin opens "$3 Dewey's", a venue needing review
- **THEN** the page shows Google's name for its place, "Three Dollar Deweys", and nothing is saved

#### Scenario: Google's name in the list, on request
- **WHEN** an admin loads the venue list
- **THEN** Google is asked for nothing, and each venue needing review has a "show Google's name" link
- **WHEN** the admin clicks it for "$3 Dewey's"
- **THEN** Google is asked for that place's name alone, and it's shown in place of the link

#### Scenario: Confident venues aren't looked up
- **WHEN** an admin opens a venue whose match is confident
- **THEN** Google isn't asked for its name

#### Scenario: Filter by reason
- **WHEN** an admin filters the list by the reason "in another state"
- **THEN** only review venues whose match failed the state check are listed

### Requirement: Lookup needs an API key and handles failures
The lookup SHALL stop with an error naming `GOOGLE_PLACES_API_KEY` when the key is not set. A failed request for one venue SHALL be reported without stopping the run, and the key SHALL NOT appear in any output.

#### Scenario: Missing key
- **WHEN** the lookup runs without `GOOGLE_PLACES_API_KEY`
- **THEN** it exits with an error naming the setting and saves nothing

#### Scenario: Failed request
- **WHEN** the request for one venue fails
- **THEN** that venue is reported as failed, keeps its previous data, and the other venues are looked up

### Requirement: Only the place ID and its coordinates are stored
For a looked-up venue, the lookup SHALL store only:
- the Google place ID;
- the place's latitude and longitude;
- the match status;
- the time the coordinates were fetched;
- for a match needing review, which of the lookup's checks it failed, and its distance from the sheet's coordinates. These are the site's own judgments about the match, not Places content. The distance SHALL be deleted whenever the coordinates are.

No other Places content SHALL be stored: not the place's name, address, business status, Maps link, website or phone. That includes stored event HTML, which keeps only coordinates. The lookup MAY use other content while it runs, to judge a match and to report closed venues, and the venue admin MAY show a review venue's name on Google, fetched when an admin asks.

#### Scenario: Confident match is stored
- **WHEN** a lookup confidently matches "Paradise Rock Club" to a place
- **THEN** the venue stores that place's ID, coordinates, the confident status and the fetch time, and nothing else from Places

#### Scenario: No other content in the database
- **WHEN** any venue has been looked up or refreshed
- **THEN** its stored fields hold no place name, address, business status, Maps link, website or phone

#### Scenario: Distance expires with the coordinates
- **WHEN** a review venue's coordinates are deleted after 30 days
- **THEN** its distance is deleted too, and its reasons stay

### Requirement: Stale coordinates are refreshed by place ID
With `--refresh-stale`, the lookup SHALL re-fetch the coordinates of each venue that has a place ID and whose coordinates are older than `--max-age-days`, which defaults to 25 days. It SHALL use Place Details on the stored place ID, requesting only the place's ID, location and business status. It SHALL NOT re-run the name search, and SHALL keep the venue's match status. If Google returns a different ID for the place, the new ID SHALL be stored.

#### Scenario: Stale coordinates
- **WHEN** a venue's coordinates were fetched 26 days ago and the lookup runs with `--refresh-stale`
- **THEN** one Place Details request is made for its place ID, and the returned coordinates and a new fetch time are stored

#### Scenario: Fresh coordinates
- **WHEN** a venue's coordinates were fetched 3 days ago
- **THEN** `--refresh-stale` makes no request for it

#### Scenario: Confirmed match survives a refresh
- **WHEN** an admin confirmed a venue's match and its coordinates are refreshed
- **THEN** the match is still confident and no name search is made

#### Scenario: Place ID changed
- **WHEN** Place Details returns a different ID for the stored place
- **THEN** the venue stores the new place ID

#### Scenario: Closed venue found while refreshing
- **WHEN** a refreshed place is reported as permanently closed
- **THEN** the run lists the venue as closed, its `is_active` is unchanged, and the status is not stored

### Requirement: Stored coordinates expire after 30 days
Every run of the lookup SHALL end by deleting the stored coordinates of each venue whose coordinates were fetched more than 30 days ago. This SHALL happen whether or not the run's requests succeeded, and also when the API key is missing. Expiry SHALL keep the place ID and match status, so a later refresh can restore the coordinates. Until then, the venue SHALL use its sheet coordinates.

#### Scenario: Refresh fails past the limit
- **WHEN** a venue's coordinates are 31 days old and its refresh request fails
- **THEN** its coordinates are deleted, its place ID and status are kept, it is reported, and its map pin falls back to the sheet coordinates

#### Scenario: Refresh fails within the limit
- **WHEN** a venue's coordinates are 26 days old and its refresh request fails
- **THEN** it keeps its coordinates and is reported as failed

#### Scenario: Missing API key
- **WHEN** the lookup runs without `GOOGLE_PLACES_API_KEY` and some venues' coordinates are older than 30 days
- **THEN** those coordinates are deleted before the run exits with an error naming the setting

#### Scenario: Expired coordinates restored
- **WHEN** a venue whose coordinates expired is refreshed successfully
- **THEN** its new coordinates are stored and used again

### Requirement: A place that no longer exists is looked up again
When Place Details reports that a stored place ID is not found, the lookup SHALL clear the venue's lookup, both its place ID and its match status, and SHALL report it. The next lookup run SHALL then search for the venue by name, as for a new venue.

#### Scenario: Place gone
- **WHEN** Place Details returns not found for a venue's place ID
- **THEN** the venue's place ID, coordinates and status are cleared, the run lists it, and the next run without `--refresh` searches for it

### Requirement: Stored event HTML follows the venue's location
When a refresh, an expiry or a cleared lookup changes a venue's location or MAP link, the stored HTML of the venue's events SHALL be re-rendered. When nothing changes, it SHALL NOT be.

#### Scenario: Coordinates expire
- **WHEN** a venue's coordinates are deleted by expiry
- **THEN** its events' stored HTML no longer contains those coordinates

#### Scenario: Refresh returns the same place
- **WHEN** a refresh returns the coordinates already stored
- **THEN** the venue's events are not re-rendered

### Requirement: Venue names are compared without trivial differences
Wherever the site decides whether another service's place is one of its venues by name (Google Places lookups, Ticketmaster venue linking, Eventbrite venue matching), two names SHALL match when, after normalizing both, they're equal or one's words appear in a row in the other's. Normalizing SHALL:
- lowercase, and remove accents and punctuation, joining an apostrophe's parts ("Eddie's" to "eddies");
- drop a trailing parenthetical, such as "(Amesbury Location)";
- treat "st" and "street", "ave" and "avenue", and "rd" and "road" as the same word;
- drop the words "the", "and", "at", "club", "hall", "music hall", "theatre", "theater", "live", "cafe", "pub", "bar", "restaurant", "grill", "tavern", "lounge", "bistro", "brewery" and "taproom", and anything from "presented by" on, unless that would leave nothing. A name that's only those words, such as "The Music Hall", SHALL match only the same name, ignoring "the" and, for Google Places, the venue's own town and state, not a name containing it.

The other checks each service makes, such as the state and the distance, SHALL be unchanged.

#### Scenario: Apostrophes and add-on words
- **WHEN** a venue named "Fast Eddie's Billiards" is compared with "Fast Eddies Billiards Cafe"
- **THEN** the names match

#### Scenario: Apostrophe inside a word
- **WHEN** "Shayna B's By The Sea" is compared with "Shayna Bs By The Sea", and "O'Brien's" with "O'Briens Pub"
- **THEN** both pairs match

#### Scenario: Accents
- **WHEN** "Cultured Cafe" is compared with "The Remedy's Cultured Café"
- **THEN** the names match

#### Scenario: Street abbreviations
- **WHEN** "25 Central Street" is compared with "25 Central St"
- **THEN** the names match

#### Scenario: Trailing parenthetical
- **WHEN** "Gametime Lanes" is compared with "Gametime Lanes & Entertainment (Amesbury Location)"
- **THEN** the names match

#### Scenario: Different places still differ
- **WHEN** "Bleacher's Bar" is compared with "The Midway", or "Thompson Speedway" with "Thompson Raceway"
- **THEN** the names don't match

#### Scenario: A name of only noise words
- **WHEN** "The Music Hall" in Portsmouth, NH is compared with "The Music Hall Lounge", with "Music Hall", and with Google's "The Music Hall, Portsmouth, NH"
- **THEN** the first pair doesn't match, and the other two do

#### Scenario: Other checks still apply
- **WHEN** a Google Places result's name now matches but it's 40 km from the venue's sheet coordinates
- **THEN** the venue still needs review, for its distance

### Requirement: Places that aren't venues need review
A Google Places result SHALL be confident only when Google doesn't type it solely as something other than a venue: a park, hiking area, natural feature, town, neighborhood, road or other area, alongside only types that say nothing either way, such as "point of interest" or "sports activity location". A place with one of those types and also a venue's type, such as an amphitheatre in a park, or with no types, SHALL count as a venue. A result that fails this SHALL need review with the reason "type", shown in the venue admin as "not a venue". The lookup MAY ask for the result's types, which it SHALL NOT store.

#### Scenario: A park with the venue's name
- **WHEN** the result for "Spicket River Brewery" is "Spicket River Greenway", typed only as a hiking area, 1.5 km away in Massachusetts
- **THEN** the venue needs review, with the reason "type"

#### Scenario: A venue in a park
- **WHEN** a result with the venue's name is typed as both an event venue and a park
- **THEN** the match is confident

### Requirement: Review venues can be checked again for their reasons
With `--review`, the lookup SHALL run the name search again for venues marked as needing review, and only those, and record the new result as a plain lookup would, including its reasons. It SHALL accept `--limit`, `--state` and `--dry-run` like a plain run. It SHALL NOT be part of the scheduled jobs.

#### Scenario: Backfilling the reasons
- **WHEN** `lookup_venue_places --review --limit 50` runs with 178 venues needing review and 500 others
- **THEN** it searches for 50 of the review venues only, and records their status and reasons

#### Scenario: Dry run
- **WHEN** it runs with `--review --dry-run`
- **THEN** it prints each venue's would-be status and reasons, and saves nothing

### Requirement: Admins can keep a venue from being looked up
The venue admin SHALL offer an action to mark the selected venues as not to be looked up, for venues with no single place, such as festivals spread across a town. It SHALL remove any matched place (its place ID, coordinates, fetch time, review reasons and distance), set the lookup status to "Not looked up (no single place)", and re-render the stored HTML of the venues' upcoming events. Such a venue SHALL use the sheet's coordinates. No lookup SHALL search for it: not a plain run, nor one with `--refresh`, `--review` or `--refresh-stale`, including when it's named with `--sheet-ids`. Clearing its lookup SHALL make it a venue the next plain run searches for again. The lookup-status filter SHALL include the new status.

#### Scenario: Marking a festival
- **WHEN** an admin selects "Porchfest" in Somerville, a venue needing review matched to a park, and chooses "Don't look up on Google"
- **THEN** its place ID, coordinates, reasons and distance are removed, its status is "Not looked up (no single place)", and its events' map pins use the sheet's coordinates

#### Scenario: The daily lookup skips it
- **WHEN** `lookup_venue_places` runs, plain or with `--refresh`, `--review` or `--refresh-stale`
- **THEN** it makes no request for a venue marked not to be looked up, and doesn't list it in its report

#### Scenario: Named explicitly
- **WHEN** `lookup_venue_places --refresh --sheet-ids` names a venue marked not to be looked up
- **THEN** it's still skipped

#### Scenario: Undoing it
- **WHEN** an admin clears the lookup of a venue marked not to be looked up
- **THEN** its status is empty, and the next plain run searches for it

#### Scenario: Filtering
- **WHEN** an admin filters the venue list by the lookup status "Not looked up (no single place)"
- **THEN** only the venues marked that way are listed
