## Purpose

Turns an event's free-text title and artists fields into a list of individual artist names, so each act on a bill can be looked up and linked on its own.

## ADDED Requirements

### Requirement: Artist names come from the artists text, split on bill separators
The system SHALL split an event's artists text into names at these separators:
- commas and semicolons;
- " / ", and "//" with or without spaces around it;
- " + ";
- " x ", as in joint billings ("Dead Poet Society x Honey Revenge");
- " w/ " and " with ";
- " feat. ", " ft. " and " featuring ".

It SHALL NOT split on "&" or "and", because these appear inside band names. It SHALL trim each name, and remove from it a leading "with" and any trailing notes in parentheses that aren't part of the name: age limits such as "(18+)", "(21+)" or "(all ages)", and "(DJ set)", "(live set)", "(live)", "(acoustic)", "(solo)" or "(full band)". It SHALL drop empty names. Names SHALL keep the order they appear in, without duplicates.

#### Scenario: Comma-separated bill
- **WHEN** an event's artists text is "Arto Vaun, Shadow Monster, Dyr Faser"
- **THEN** its names are "Arto Vaun", "Shadow Monster" and "Dyr Faser", in that order

#### Scenario: Double slashes
- **WHEN** an event's artists text is "Bomb Valley// Blesser //Seconds Before the Crash// Silvera"
- **THEN** its names are "Bomb Valley", "Blesser", "Seconds Before the Crash" and "Silvera"

#### Scenario: Featuring and with
- **WHEN** an event's artists text is "Genevieve Artadi ft. Louis Cole w/ Chiquita Magic"
- **THEN** its names are "Genevieve Artadi", "Louis Cole" and "Chiquita Magic"

#### Scenario: Leading "with" and age limits removed
- **WHEN** an event's artists text is "with Jacyn Tremblay, Rhiannon Hurst (21+)"
- **THEN** its names are "Jacyn Tremblay" and "Rhiannon Hurst"

#### Scenario: Joint billing and set notes
- **WHEN** an event's artists text is "Dead Poet Society x Honey Revenge, 49th & Main (DJ Set) (21+)"
- **THEN** its names are "Dead Poet Society", "Honey Revenge" and "49th & Main"

#### Scenario: Ampersand kept
- **WHEN** an event's artists text is "Simon & Garfunkel Story, Mumford & Sons"
- **THEN** its names are "Simon & Garfunkel Story" and "Mumford & Sons"

### Requirement: The title adds the headliner when it names one
The system SHALL also take names from the event's title, after removing:
- a leading presenter phrase, ending in "Presents:" or "presents";
- a leading "An evening with".

The title SHALL be split with the same separators as the artists text, and its names SHALL come before the artists text's names. A title name that contains "tribute", "party", "night", "festival", "open mic" or "karaoke", ignoring case, SHALL be dropped. The check SHALL be made after the show name is removed (see the next requirement), so that a band's name survives a show name that calls it a tribute.

#### Scenario: Headliner only in the title
- **WHEN** an event is titled "SHEBAD w/ Psymon Spine + A Halloween Surprise", and its artists text is "SHEBAD, Psymon Spine"
- **THEN** its names are "SHEBAD", "Psymon Spine" and "A Halloween Surprise"

#### Scenario: Presenter prefix removed
- **WHEN** an event is titled "State Theatre Presents: The Ballroom Thieves"
- **THEN** its names include "The Ballroom Thieves", and don't include "State Theatre"

#### Scenario: Tribute title ignored
- **WHEN** an event is titled "Dirty Deeds AC/DC Tribute", and its artists text is "Highway Kind"
- **THEN** its only name is "Highway Kind"

#### Scenario: Tribute only in the show name
- **WHEN** an event is titled "Damn the Torpedoes - a Tribute To Tom Petty"
- **THEN** its name is "Damn the Torpedoes"

### Requirement: A show or tour name after a dash or colon is dropped
In each name, from the title or the artists text, everything from the first spaced dash (" - ", " – ", " — ", or a dash with a space before it) or colon followed by a space SHALL be dropped. That part names the show or tour, not the artist. A dash without a space before it, as in "GA-20" or "Jay-Z", SHALL be kept. Names after a separator that follows the show name SHALL still be taken.

#### Scenario: Show names dropped
- **WHEN** events are titled "Còig - early show", "Corey Kent - Heartland Rock and Roll", "Dark Star Orchestra - Celebrating 45 Years of Reckoning" and "2hollis: The Pirouette Tour"
- **THEN** their names are "Còig", "Corey Kent", "Dark Star Orchestra" and "2hollis"

#### Scenario: Tour names dropped
- **WHEN** one event is titled "GA-20 / Sue Foley: Together for the Holidays Tour (18+)", and another "Blue October - 'Foiled' 20th Anniversary World Tour"
- **THEN** the first event's names are "GA-20" and "Sue Foley", and the second's is "Blue October"

#### Scenario: Openers after the show name
- **WHEN** an event is titled "Bumpin Uglies - Orange Crush Tour W/ Artikal Sound System, Joey Harkum"
- **THEN** its names are "Bumpin Uglies", "Artikal Sound System" and "Joey Harkum"

### Requirement: Placeholder names are dropped
The system SHALL drop these names, ignoring case:
- "TBA" and "TBD";
- "special guest(s)" and "and more";
- "Organization";
- "DJ" on its own;
- any name of a single character.

The system SHALL extract no names from events whose kind isn't music.

#### Scenario: Placeholders
- **WHEN** an event's artists text is "Organization" and its title is "Fruition + Special Guests"
- **THEN** its only name is "Fruition"

#### Scenario: Non-music event
- **WHEN** an event's kind is "Other (not music)"
- **THEN** it has no names
