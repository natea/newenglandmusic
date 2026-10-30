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

### Requirement: A show or tour name after a dash or colon is dropped
In each name, from the title or the artists text, everything from the first spaced dash (" - ", " – ", " — ", or a dash with a space before it) or colon followed by a space SHALL be dropped. That part names the show or tour, not the artist. A dash without a space before it, as in "GA-20" or "Jay-Z", SHALL be kept. Names after a separator that follows the show name SHALL still be taken. A tour named after the act with no dash or colon between, as in "Seb Lowe US 2027", SHALL also be dropped: a trailing run of years, "tour", and region or season words (US, UK, North, American, World, Fall, Summer and the like), only when the run has a year, or "tour" with a region or season, in it, and the word before it isn't a little word like "the" or "of".

#### Scenario: Show names dropped
- **WHEN** events are titled "Còig - early show", "Corey Kent - Heartland Rock and Roll", "Dark Star Orchestra - Celebrating 45 Years of Reckoning" and "2hollis: The Pirouette Tour"
- **THEN** their names are "Còig", "Corey Kent", "Dark Star Orchestra" and "2hollis"

#### Scenario: Tour names dropped
- **WHEN** one event is titled "GA-20 / Sue Foley: Together for the Holidays Tour (18+)", and another "Blue October - 'Foiled' 20th Anniversary World Tour"
- **THEN** the first event's names are "GA-20" and "Sue Foley", and the second's is "Blue October"

#### Scenario: Openers after the show name
- **WHEN** an event is titled "Bumpin Uglies - Orange Crush Tour W/ Artikal Sound System, Joey Harkum"
- **THEN** its names are "Bumpin Uglies", "Artikal Sound System" and "Joey Harkum"

#### Scenario: A tour name with no separator
- **WHEN** events are titled "Seb Lowe US 2027", "Built to Spill Fall 2026 Tour" and "Matchbox Twenty North American Tour 2026"
- **THEN** their names are "Seb Lowe", "Built to Spill" and "Matchbox Twenty"

#### Scenario: Names that only look like tours
- **WHEN** events are titled "Summer Salt", "North Mississippi Allstars", "Class of 2027" and "The Thing in the Spring 2027"
- **THEN** each name is kept whole
