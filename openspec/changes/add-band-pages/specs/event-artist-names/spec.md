## MODIFIED Requirements

### Requirement: The title adds the headliner when it names one
The system SHALL also take names from the event's title, after removing:
- a leading presenter phrase, ending in "Presents:" or "presents";
- a leading "An evening with".

The title SHALL be split with the same separators as the artists text, and its names SHALL come before the artists text's names. A title name that names a kind of night rather than an act SHALL be dropped: one containing, ignoring case, "tribute", "party", "night", "festival", "open mic", "karaoke", "jam", "session", "brunch", "live music", "open stage", "series", "showcase", "christmas", "halloween", "intimate evening", "welcomes", "battle of the bands", "live" followed by a genre or "band" ("Live Jazz", "Live Band"), or a weekday in the plural ("Wednesdays"); one with a word ending in "fest" ("Porchfest"); or one that is only "free". "Tour" is not among them, so "Built to Spill Fall 2026 Tour" keeps its act. The check SHALL be made after the show name is removed (see the next requirement), so that a band's name survives a show name that calls it a tribute.

#### Scenario: Headliner only in the title
- **WHEN** an event is titled "SHEBAD w/ Psymon Spine + Shadow Show", and its artists text is "SHEBAD, Psymon Spine"
- **THEN** its names are "SHEBAD", "Psymon Spine" and "Shadow Show"

#### Scenario: Presenter prefix removed
- **WHEN** an event is titled "State Theatre Presents: The Ballroom Thieves"
- **THEN** its names include "The Ballroom Thieves", and don't include "State Theatre"

#### Scenario: Tribute title ignored
- **WHEN** an event is titled "Dirty Deeds AC/DC Tribute", and its artists text is "Highway Kind"
- **THEN** its only name is "Highway Kind"

#### Scenario: Tribute only in the show name
- **WHEN** an event is titled "Damn the Torpedoes - a Tribute To Tom Petty"
- **THEN** its name is "Damn the Torpedoes"

#### Scenario: Kinds of night named in titles
- **WHEN** events are titled "Irish Session", "Jazz Jam", "Live Music at SAL's Birch Bar", "Live Jazz", "Jazz Wednesdays", "Porchfest", "A Celtic Christmas" and "FREE"
- **THEN** none of those titles gives a name, while "They Might Be Giants", "Free Throw", "Evening Hymns" and "Live Wire" each give theirs
