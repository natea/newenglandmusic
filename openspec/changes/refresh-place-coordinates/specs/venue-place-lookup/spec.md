## ADDED Requirements

### Requirement: Only the place ID and its coordinates are stored
For a looked-up venue, the lookup SHALL store only:
- the Google place ID;
- the place's latitude and longitude;
- the match status;
- the time the coordinates were fetched.

No other Places content SHALL be stored: not the place's name, address, business status, Maps link, website or phone. That includes stored event HTML, which keeps only coordinates. The lookup MAY use other content while it runs, to judge a match and to report closed venues.

#### Scenario: Confident match is stored
- **WHEN** a lookup confidently matches "Paradise Rock Club" to a place
- **THEN** the venue stores that place's ID, coordinates, the confident status and the fetch time, and nothing else from Places

#### Scenario: No other content in the database
- **WHEN** any venue has been looked up or refreshed
- **THEN** its stored fields hold no place name, address, business status, Maps link, website or phone

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

## MODIFIED Requirements

### Requirement: Only confident matches are used
A result SHALL be stored as confident only when its name matches the venue's name, its address is in the venue's state, and it lies within 25 km of the venue's sheet coordinates (or the venue has none). Any other result SHALL be stored as needing review.

#### Scenario: Confident match
- **WHEN** the top result is "Paradise Rock Club presented by Citizens" at 967 Commonwealth Ave, Boston, MA, 1 km from the sheet's coordinates
- **THEN** its place ID and coordinates are saved and the match is marked confident

#### Scenario: Wrong place
- **WHEN** the top result has a different name, is in another state, or is more than 25 km away
- **THEN** it is saved as needing review and its coordinates are not used anywhere

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
The venue admin SHALL show the place ID, the looked-up coordinates, when they were fetched and a Google Maps link from the place ID. It SHALL filter by lookup status, and SHALL let an admin mark a match needing review as confident, or clear a venue's lookup.

#### Scenario: Confirming a match
- **WHEN** an admin marks a venue's review-needed match as confident
- **THEN** its looked-up location is used from then on

#### Scenario: Clearing a lookup
- **WHEN** an admin clears a venue's lookup
- **THEN** its looked-up fields are emptied and the next lookup run searches for it again
