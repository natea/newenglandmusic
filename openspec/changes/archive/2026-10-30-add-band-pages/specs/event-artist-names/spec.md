## MODIFIED Requirements

### Requirement: The title adds the headliner when it names one
The system SHALL also take names from the event's title, after removing:
- a leading presenter phrase, ending in "Presents:" or "presents";
- a leading "An evening with".

The title SHALL be split with the same separators as the artists text, and its names SHALL come before the artists text's names. A title name that names a kind of night rather than an act SHALL be dropped: one containing, ignoring case, "tribute", "party", "night", "festival", "open mic", "karaoke", "jam", "session", "brunch", "live music", "open stage", "series", "showcase", "christmas", "halloween", "intimate evening", "welcomes", "battle of the bands", "music of", "songs of", "live" followed by a genre or "band" ("Live Jazz", "Live Band"), a weekday in the plural ("Wednesdays"), or a weekday followed by a genre ("Sunday Blues"); one with a word ending in "fest" ("Porchfest"); or one that is only "free". "Tour" is not among them, so "Built to Spill Fall 2026 Tour" keeps its act. The check SHALL be made after the show name is removed (see the next requirement), so that a band's name survives a show name that calls it a tribute.

#### Scenario: Headliner only in the title
- **WHEN** an event is titled "SHEBAD w/ Psymon Spine + Shadow Show", and its artists text is "SHEBAD, Psymon Spine"
- **THEN** its names are "SHEBAD", "Psymon Spine" and "Shadow Show"

#### Scenario: Presenter prefix removed
- **WHEN** an event is titled "State Theatre Presents: The Ballroom Thieves"
- **THEN** its names include "The Ballroom Thieves", and don't include "State Theatre"

#### Scenario: Tribute title ignored
- **WHEN** an event is titled "Dirty Deeds AC/DC Tribute", and its artists text is "Highway Kind"
- **THEN** its only name is "Highway Kind"

#### Scenario: A tribute named by "the music of"
- **WHEN** an event is titled "The music of Steely Dan"
- **THEN** its title gives no names

#### Scenario: Tribute only in the show name
- **WHEN** an event is titled "Damn the Torpedoes - a Tribute To Tom Petty"
- **THEN** its name is "Damn the Torpedoes"

#### Scenario: Kinds of night named in titles
- **WHEN** events are titled "Irish Session", "Jazz Jam", "Live Music at SAL's Birch Bar", "Live Jazz", "Jazz Wednesdays", "Porchfest", "A Celtic Christmas" and "FREE"
- **THEN** none of those titles gives a name, while "They Might Be Giants", "Free Throw", "Evening Hymns" and "Live Wire" each give theirs

### Requirement: A show or tour name after a dash or colon is dropped
In each name, from the title or the artists text, everything from the first spaced dash (a dash with a space before or after it) or colon followed by a space SHALL be dropped. That part names the show or tour, not the artist. A dash with no space on either side, as in "GA-20" or "Jay-Z", SHALL be kept. Names after a separator that follows the show name SHALL still be taken, except a piece after a comma that ends in "tour", which is more of the show name ("Bo Staloch - The 'Too Big, Too Big' Tour"). A tour named after the act with no dash or colon between, as in "Seb Lowe US 2027", SHALL also be dropped: a trailing run of years, "tour", and region or season words (US, UK, North, American, World, Fall, Summer and the like), only when the run has a year, or "tour" with a region or season, in it, and the word before it isn't a little word like "the" or "of".

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



### Requirement: Artist names come from the artists text, split on bill separators
The system SHALL split an event's artists text into names at these separators:
- commas and semicolons, taking a comma followed by "&" or "and" (a serial comma, as in "DÀN, & Aydan Hill") as one separator;
- "/" with a space on at least one side ("Sue Foley/ GA-20"; "AC/DC" stays whole), and "//" with or without spaces around it;
- " + ";
- " x ", as in joint billings ("Dead Poet Society x Honey Revenge");
- " w/ " (also written "w /") and " with ";
- " feat. ", " ft. " and " featuring ".

It SHALL NOT split on "&" or "and" without a comma before it, because these appear inside band names. It SHALL trim each name, and remove from it a leading "with", "members of", "special guest(s)" or "a special appearance by", a trailing "& friends", "and friends", "& guests", "& special guests" or "& band" ("Sammy Rae & The Friends" is a band, and stays whole), any trailing note in square brackets, parentheses or stars, all of which are notes rather than part of a name ("[EARLY SHOW]", "(21+)", "(DJ Set)", "(formerly of The Eagles)", "* SOLD OUT *"), a trailing "** SOLD OUT", a venue after "@" or "live at", and a quoted tour ("THE BOUNCING SOULS 'Born To Be Tour'"); and it SHALL read an escaped apostrophe ("\'") as an apostrophe. It SHALL drop empty names. Names SHALL keep the order they appear in, without duplicates.

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

#### Scenario: Serial comma before the last name
- **WHEN** one event is titled "AYĖL, Belen, DÀN, & Aydan Hill", and another's artists text is "SixFoxWhiskey, Booyah, and The Hub"
- **THEN** the first's names are "AYĖL", "Belen", "DÀN" and "Aydan Hill", and the second's "SixFoxWhiskey", "Booyah" and "The Hub"

#### Scenario: One-sided slashes and dashes
- **WHEN** an event is titled "Sue Foley/ GA-20 Together for the Holidays- Sportsmens"
- **THEN** its names are "Sue Foley" and "GA-20 Together for the Holidays"

#### Scenario: "w /", bracketed notes, friends and members
- **WHEN** one event is titled "State Theatre Presents: Talib Kweli w / Graphic Melee [EARLY SHOW]", and others' artists are "Alan Kaufman & friends" and "members of SixFoxWhiskey, Booyah"
- **THEN** their names are "Talib Kweli" and "Graphic Melee"; "Alan Kaufman"; and "SixFoxWhiskey" and "Booyah"

#### Scenario: A comma inside a tour name
- **WHEN** events are titled "Bo Staloch - The 'Too Big, Too Big' Tour" and "Bo Staloch: The Too Big, Too Big Tour"
- **THEN** each one's only name is "Bo Staloch"

#### Scenario: "Evening With" and a weekday's genre
- **WHEN** events are titled "Evening With - John Splithoff Stripped Tour" and "Sunday Blues with Bruce Bears & Friends"
- **THEN** the first's name is "John Splithoff Stripped Tour", and the second's "Bruce Bears"

#### Scenario: Notes, venues and lead-ins dropped
- **WHEN** an event's artists are "Don Felder (formerly of The Eagles), Mike Dawes (rescheduled from 1/28), a Special Appearance by Sarah Lee Guthrie", and others are titled "Q Marsden ** SOLD OUT", "The Hellp (DJ Set) @ 99 Scott", "Sophistafunk Live at The Main Pub" and "THE BOUNCING SOULS 'Born To Be Tour'"
- **THEN** their names are "Don Felder", "Mike Dawes" and "Sarah Lee Guthrie"; "Q Marsden"; "The Hellp"; "Sophistafunk"; and "THE BOUNCING SOULS"
