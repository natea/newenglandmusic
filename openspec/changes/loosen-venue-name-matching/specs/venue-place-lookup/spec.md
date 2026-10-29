## ADDED Requirements

### Requirement: Venue names are compared without trivial differences
Wherever the site decides whether another service's place is one of its venues by name (Google Places lookups, Ticketmaster venue linking, Eventbrite venue matching), two names SHALL match when, after normalizing both, they're equal or one's words appear in a row in the other's. Normalizing SHALL:
- lowercase, and remove accents and punctuation, joining an apostrophe's parts ("Eddie's" to "eddies");
- drop a trailing parenthetical, such as "(Amesbury Location)";
- treat "st" and "street", "ave" and "avenue", and "rd" and "road" as the same word;
- drop the words "the", "and", "at", "club", "hall", "music hall", "theatre", "theater", "live", "cafe", "pub", "bar", "restaurant", "grill", "tavern", "lounge", "bistro", "brewery" and "taproom", and anything from "presented by" on, unless that would leave nothing.

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

#### Scenario: Other checks still apply
- **WHEN** a Google Places result's name now matches but it's 40 km from the venue's sheet coordinates
- **THEN** the venue still needs review, for its distance
