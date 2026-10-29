## MODIFIED Requirements

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

### Requirement: Admins can settle uncertain matches
The venue admin SHALL show the place ID, the looked-up coordinates, when they were fetched and a Google Maps link from the place ID. It SHALL filter by lookup status, and SHALL let an admin mark a match needing review as confident, or clear a venue's lookup. For a match needing review, the list SHALL show a "Why review" column naming its reasons in words ("name differs", "in another state", "38 km away"), and SHALL filter by each reason. Marking a match confident, or clearing a lookup, SHALL clear its reasons and distance.

#### Scenario: Confirming a match
- **WHEN** an admin marks a venue's review-needed match as confident
- **THEN** its looked-up location is used from then on

#### Scenario: Clearing a lookup
- **WHEN** an admin clears a venue's lookup
- **THEN** its looked-up fields are emptied and the next lookup run searches for it again

#### Scenario: Why a venue needs review
- **WHEN** an admin opens the venue list filtered to "Needs review"
- **THEN** each venue shows why, such as "name differs · 0.4 km away" for $3 Dewey's

#### Scenario: Filter by reason
- **WHEN** an admin filters the list by the reason "in another state"
- **THEN** only review venues whose match failed the state check are listed

### Requirement: Only the place ID and its coordinates are stored
For a looked-up venue, the lookup SHALL store only:
- the Google place ID;
- the place's latitude and longitude;
- the match status;
- the time the coordinates were fetched;
- for a match needing review, which of the lookup's checks it failed, and its distance from the sheet's coordinates. These are the site's own judgments about the match, not Places content. The distance SHALL be deleted whenever the coordinates are.

No other Places content SHALL be stored: not the place's name, address, business status, Maps link, website or phone. That includes stored event HTML, which keeps only coordinates. The lookup MAY use other content while it runs, to judge a match and to report closed venues.

#### Scenario: Confident match is stored
- **WHEN** a lookup confidently matches "Paradise Rock Club" to a place
- **THEN** the venue stores that place's ID, coordinates, the confident status and the fetch time, and nothing else from Places

#### Scenario: No other content in the database
- **WHEN** any venue has been looked up or refreshed
- **THEN** its stored fields hold no place name, address, business status, Maps link, website or phone

#### Scenario: Distance expires with the coordinates
- **WHEN** a review venue's coordinates are deleted after 30 days
- **THEN** its distance is deleted too, and its reasons stay

## ADDED Requirements

### Requirement: Review venues can be checked again for their reasons
With `--review`, the lookup SHALL run the name search again for venues marked as needing review, and only those, and record the new result as a plain lookup would, including its reasons. It SHALL accept `--limit`, `--state` and `--dry-run` like a plain run. It SHALL NOT be part of the scheduled jobs.

#### Scenario: Backfilling the reasons
- **WHEN** `lookup_venue_places --review --limit 50` runs with 178 venues needing review and 500 others
- **THEN** it searches for 50 of the review venues only, and records their status and reasons

#### Scenario: Dry run
- **WHEN** it runs with `--review --dry-run`
- **THEN** it prints each venue's would-be status and reasons, and saves nothing
