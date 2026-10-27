## Purpose

Turns an event's free-text title and artists fields into a list of individual artist names, so each act on a bill can be looked up and linked on its own.

## ADDED Requirements

### Requirement: Artist names come from the artists text, split on bill separators
The system SHALL split an event's artists text into names at these separators:
- commas and semicolons;
- " / ";
- " + ";
- " w/ " and " with ";
- " feat. ", " ft. " and " featuring ".

It SHALL NOT split on "&" or "and", because these appear inside band names. It SHALL trim each name and drop empty ones. Names SHALL keep the order they appear in, without duplicates.

#### Scenario: Comma-separated bill
- **WHEN** an event's artists text is "Arto Vaun, Shadow Monster, Dyr Faser"
- **THEN** its names are "Arto Vaun", "Shadow Monster" and "Dyr Faser", in that order

#### Scenario: Featuring and with
- **WHEN** an event's artists text is "Genevieve Artadi ft. Louis Cole w/ Chiquita Magic"
- **THEN** its names are "Genevieve Artadi", "Louis Cole" and "Chiquita Magic"

#### Scenario: Ampersand kept
- **WHEN** an event's artists text is "Simon & Garfunkel Story, Mumford & Sons"
- **THEN** its names are "Simon & Garfunkel Story" and "Mumford & Sons"

### Requirement: The title adds the headliner when it names one
The system SHALL also take names from the event's title, after removing:
- a leading presenter phrase, ending in "Presents:" or "presents";
- a leading "An evening with".

The title SHALL be split with the same separators as the artists text, and its names SHALL come before the artists text's names. A title that contains "tribute", "party", "night", "festival", "open mic" or "karaoke", ignoring case, SHALL contribute no names.

#### Scenario: Headliner only in the title
- **WHEN** an event is titled "SHEBAD w/ Psymon Spine + A Halloween Surprise", and its artists text is "SHEBAD, Psymon Spine"
- **THEN** its names are "SHEBAD", "Psymon Spine" and "A Halloween Surprise"

#### Scenario: Presenter prefix removed
- **WHEN** an event is titled "State Theatre Presents: The Ballroom Thieves"
- **THEN** its names include "The Ballroom Thieves", and don't include "State Theatre"

#### Scenario: Tribute title ignored
- **WHEN** an event is titled "A Super Fine John Prine Time: a John Prine tribute", and its artists text is "Highway Kind"
- **THEN** its only name is "Highway Kind"

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
