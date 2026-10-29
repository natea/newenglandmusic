## ADDED Requirements

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
