# Spec Delta

## Purpose

Finds each venue on Google Places and records its exact location, address, open/closed status and links, kept apart from the sheet's town-level data, so the site and venue matching can rely on where a venue really is.

## ADDED Requirements

### Requirement: Venues are looked up by name and town
The lookup SHALL search Google Places for each venue by name, town and state, biased to the venue's sheet coordinates when it has them, and SHALL consider only the top results.

#### Scenario: Venue found
- **WHEN** the lookup runs for "Paradise Rock Club" in Allston, MA
- **THEN** the search text includes the venue's name, town and state, and the request is biased toward the venue's sheet coordinates

### Requirement: Only confident matches are used
A result SHALL be stored as confident only when its name matches the venue's name, its address is in the venue's state, and it lies within 25 km of the venue's sheet coordinates (or the venue has none). Any other result SHALL be stored as needing review.

#### Scenario: Confident match
- **WHEN** the top result is "Paradise Rock Club presented by Citizens" at 967 Commonwealth Ave, Boston, MA, 1 km from the sheet's coordinates
- **THEN** its place ID, address, coordinates, status and Maps link are saved and the match is marked confident

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
- **THEN** its business status is saved, the venue's `is_active` is unchanged, and the lookup lists it as closed so the sheet can be updated

### Requirement: Exact locations are used where known
A venue's location SHALL be its confident looked-up coordinates when present, and its sheet coordinates otherwise. This location SHALL be used for its map pin, its "MAP" link and Ticketmaster venue matching. The "MAP" link SHALL be the place's Google Maps link when there is a confident match.

#### Scenario: Looked-up venue
- **WHEN** an event's venue has a confident looked-up location
- **THEN** the event page's map pin and MAP link use that location

#### Scenario: Match needing review
- **WHEN** a venue's lookup needs review
- **THEN** its sheet coordinates are used, as before the lookup

### Requirement: Lookups are repeatable and cheap
The lookup SHALL skip venues already looked up unless told to refresh. It SHALL accept venue sheet IDs, a state filter and a limit, and SHALL support a dry run that saves nothing. By default it SHALL request only Pro-tier fields; website and phone SHALL be requested only when asked for.

#### Scenario: Second run
- **WHEN** the lookup runs twice
- **THEN** the second run makes no requests for venues looked up by the first

#### Scenario: Dry run
- **WHEN** the lookup runs with `--dry-run`
- **THEN** it reports what it found and saves nothing

#### Scenario: Contact details requested
- **WHEN** the lookup runs with `--contact`
- **THEN** the venue's website and phone are requested and saved

### Requirement: Admins can settle uncertain matches
The venue admin SHALL show the looked-up fields, filter by lookup status and business status, and let an admin mark a match needing review as confident, or clear a venue's lookup.

#### Scenario: Confirming a match
- **WHEN** an admin marks a venue's review-needed match as confident
- **THEN** its looked-up location is used from then on

#### Scenario: Clearing a lookup
- **WHEN** an admin clears a venue's lookup
- **THEN** its looked-up fields are emptied and the next lookup run searches for it again

### Requirement: Lookup needs an API key and handles failures
The lookup SHALL stop with an error naming `GOOGLE_PLACES_API_KEY` when the key is not set. A failed request for one venue SHALL be reported without stopping the run, and the key SHALL NOT appear in any output.

#### Scenario: Missing key
- **WHEN** the lookup runs without `GOOGLE_PLACES_API_KEY`
- **THEN** it exits with an error naming the setting and saves nothing

#### Scenario: Failed request
- **WHEN** the request for one venue fails
- **THEN** that venue is reported as failed, keeps its previous data, and the other venues are looked up
