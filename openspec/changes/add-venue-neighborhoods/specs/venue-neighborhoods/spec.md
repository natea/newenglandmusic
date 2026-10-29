## Purpose

Gives each venue in a city the neighborhood it's in, from OpenStreetMap, so events can say "Boston (West End)" and visitors can narrow a town to its neighborhoods.

## ADDED Requirements

### Requirement: A venue is found on OpenStreetMap by its own name and town
`lookup_venue_neighborhoods` SHALL search Nominatim for each active venue that has a town and state and is due, with the query "<venue name>, <town>, <state>", limited to the US, asking for address details. It SHALL accept the first result whose normalized name equals the venue's normalized name, or contains it as whole words, and whose address names the venue's town and state. It SHALL NOT send Google Places coordinates, or any other Google data, to any service. A venue with no accepted result SHALL be recorded as not found, with no neighborhood.

A venue SHALL be due when it was never looked up, or was looked up more than 365 days ago, and its neighborhood wasn't set by an editor. `--limit` SHALL cap the venues looked up in a run, `--sheet-ids` SHALL name venues to look up whether due or not, and `--dry-run` SHALL report without saving.

#### Scenario: Venue found
- **WHEN** Nominatim's first result for "Big Night Live, Boston, MA" is named "Big Night Live", in Boston, MA, with the suburb "West End"
- **THEN** the venue's neighborhood is "West End", from OpenStreetMap

#### Scenario: A different place with the town's name
- **WHEN** the only result for "The Sinclair, Cambridge, MA" is a bus stop named "Cambridge"
- **THEN** the venue is recorded as not found, with no neighborhood

#### Scenario: Google data never sent
- **WHEN** a venue has Google Places coordinates
- **THEN** the requests to Nominatim and Overpass contain neither them nor its place ID

### Requirement: The neighborhood is the most familiar name OpenStreetMap gives
From the accepted result's address, the command SHALL choose, in this order, the first usable value of "suburb", "quarter", "neighbourhood" and "city_district". A value SHALL NOT be usable when:
- it ends in "Historic District";
- it equals the venue's town;
- it names a borough or county, such as "Brooklyn" for a venue in New York, or "Kings County".

#### Scenario: Suburb preferred
- **WHEN** the address has the neighbourhood "Grays Ferry" and the suburb "South Philadelphia"
- **THEN** the neighborhood is "South Philadelphia"

#### Scenario: Historic district skipped
- **WHEN** the address has the neighbourhood "Ninth Square Historic District" and the suburb "Dixwell"
- **THEN** the neighborhood is "Dixwell"

#### Scenario: Only the borough
- **WHEN** a Brooklyn venue's address has only the suburb "Brooklyn" and the city district "Kings County"
- **THEN** no name from the address is used, and the nearest-point fallback is tried

### Requirement: Where neighborhoods are only points, the nearest one is used
When the address gives no usable name, the command SHALL ask Overpass for nodes tagged `place=neighbourhood`, `place=suburb` or `place=quarter` within 1.5 km of the result's location, and use the nearest one's name, if it's usable. Overpass SHALL be retried after 5, 15 and 45 seconds on a timeout or a 429, 502, 503 or 504, and tried on a mirror after that. When it still fails, the venue SHALL be left due, for the next run.

#### Scenario: Williamsburg
- **WHEN** the Brooklyn venue's nearest neighborhood point is "Williamsburg", 400 m away
- **THEN** its neighborhood is "Williamsburg", from Overpass

#### Scenario: Overpass busy
- **WHEN** Overpass and its mirror time out on every try
- **THEN** the venue is unchanged and still due, and the run carries on

### Requirement: Lookups are polite and the run stops cleanly
Nominatim SHALL get at most one request a second, and every request SHALL send the site's contact user agent. On a Nominatim 429 or 403, the run SHALL stop, keep what it found, and report the venues left. Neighborhoods SHALL be saved with `queryset.update()`, and only venues whose neighborhood changed SHALL have their events re-rendered. The run SHALL record a `JobRun` with counts of venues looked up, found, given a neighborhood (from the address or from Overpass), not found, failed and left.

#### Scenario: Nominatim blocks
- **WHEN** Nominatim answers 429 after ten venues
- **THEN** the run stops, keeps the ten, and reports the rest as left

#### Scenario: Paced
- **WHEN** a run looks up three venues
- **THEN** its Nominatim requests are at least a second apart

### Requirement: Events show their venue's neighborhood
An event at a venue with a neighborhood SHALL show it after the venue's town, in parentheses, as "Boston (West End)". Events at venues without one, and events with a venue override, SHALL look as they do now. A neighborhood change SHALL re-render the stored HTML of the venue's upcoming events.

#### Scenario: Shown
- **WHEN** Big Night Live's neighborhood is "West End"
- **THEN** its events read "@ Big Night Live, Boston (West End)"

#### Scenario: Changed
- **WHEN** a venue's neighborhood changes from none to "Old Port"
- **THEN** its upcoming events' stored HTML shows "Portland (Old Port)"

### Requirement: Editors can set or clear a venue's neighborhood
The venue admin SHALL show the neighborhood, where it came from (OpenStreetMap address, Overpass, or editor) and when it was looked up, with a filter by source. An editor SHALL be able to type a neighborhood, or tick "no neighborhood". Either SHALL record the editor as the source, and later runs SHALL NOT change it. Saving SHALL re-render the venue's events.

#### Scenario: Editor sets one
- **WHEN** an editor sets 9:30 Club's neighborhood to "U Street"
- **THEN** its events show "Washington (U Street)", and later runs leave it

### Requirement: OpenStreetMap is credited
Every page that can show a neighborhood SHALL credit "© OpenStreetMap contributors", with a link to `https://www.openstreetmap.org/copyright`, in its footer. `/privacy` SHALL list OpenStreetMap among the site's data sources.

#### Scenario: Credit
- **WHEN** the listing renders
- **THEN** its footer links "© OpenStreetMap contributors" to the copyright page
