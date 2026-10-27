## Purpose

Lets visitors sample an act on Spotify straight from the events listing. Each artist name is linked to its Spotify artist where one clearly exists, and the site keeps only the Spotify ID, for a limited time.

## ADDED Requirements

### Requirement: Artist names are matched to Spotify artists only on an unambiguous exact match
`match_spotify_artists` SHALL collect the artist names of upcoming approved music events. It SHALL search Spotify for each name that has no link yet, or whose automatic link is due for a re-check. The search SHALL use the Client Credentials flow, with type `artist` and a limit of 10.

The command SHALL record each name as one of:
- **matched**, with the Spotify artist ID, when exactly one result has the same normalized name. Normalizing ignores case, accents, punctuation and a leading "The", and treats "&" as "and".
- **ambiguous**, when more than one result has the same normalized name.
- **not found**, when no result does.

Names SHALL be stored in normalized form, so that the same artist across many events is searched once. When `SPOTIFY_CLIENT_ID` or `SPOTIFY_CLIENT_SECRET` is unset, the command SHALL print that Spotify isn't configured, exit successfully and change nothing. `--dry-run` SHALL report what it would record without saving it.

#### Scenario: Unique exact match
- **WHEN** a search for "The Ballroom Thieves" returns one artist named "The Ballroom Thieves" and others with different names
- **THEN** the name is recorded as matched, with that artist's ID

#### Scenario: Two artists with the same name
- **WHEN** a search for "Epicenter" returns two artists, each named "Epicenter"
- **THEN** the name is recorded as ambiguous, with no ID

#### Scenario: No exact match
- **WHEN** a search for "Haven's Den" returns only "Haven" and "The Den"
- **THEN** the name is recorded as not found

#### Scenario: Same name on many events
- **WHEN** "Lake Street Dive" appears on four upcoming events
- **THEN** Spotify is searched for it once

#### Scenario: Not configured
- **WHEN** the command runs without Spotify credentials
- **THEN** it makes no request, saves nothing, and exits with status 0

#### Scenario: Dry run
- **WHEN** the command runs with `--dry-run`
- **THEN** it prints each name's would-be status, and saves nothing

### Requirement: Duo billings and occasions fall back to their artists
When a name isn't an artist, the system SHALL try two fallbacks.

**Duo billings.** A name made of acts joined by "&" or "and", such as "Connor Garvey & Ben Cosgrove", SHALL have each act searched, when:
- the whole name was searched and recorded as not found;
- every act has two or more words, so "Mumford & Sons" and "Simon & Garfunkel" are never split.

A backing band after "and his", "and her" or "and their" SHALL NOT be searched on its own. Each matched act SHALL get its own play button.

**Occasions.** A name that starts with an artist's name, followed by words that name an occasion (tour, annual, anniversary, concert, show, celebration, residency, release, holiday, christmas, benefit, charity, reunion, farewell, birthday, edition), SHALL be shown with that artist's play button. The button SHALL be labelled with the artist's part of the name. Such a name SHALL NOT be searched when the artist is already matched. When the artist isn't matched yet, and the name's own search finds no exact match but does find exactly one artist whose name the event's name starts with, that artist SHALL be matched under its own name. An editor's link SHALL never be overwritten this way.

The acts and artists found this way SHALL count as seen whenever the name that led to them is on an upcoming event. `--limit` SHALL count every search, fallbacks included.

#### Scenario: Duo split when it isn't an artist
- **WHEN** "Chris Collins & Boulder Canyon" is searched and not found, and "Boulder Canyon" is then found
- **THEN** "Chris Collins" and "Boulder Canyon" are searched in the same run, and the event shows a "Boulder Canyon" button

#### Scenario: Duo that is an artist
- **WHEN** "AJ Lee & Blue Summit" is an artist on Spotify
- **THEN** it's matched whole, and its acts aren't searched

#### Scenario: Backing band
- **WHEN** "Chris Cote and his Band of These Guys" isn't an artist
- **THEN** only "Chris Cote" is searched next

#### Scenario: Occasion of a known artist
- **WHEN** "Built to Spill" is matched, and an event is titled "Built to Spill Fall 2026 Tour"
- **THEN** the event shows a "Built to Spill" button, and the title isn't searched

#### Scenario: Occasion found in its own search
- **WHEN** a search for "Corey Kent Heartland Rock and Roll Tour" finds no exact match, but finds one artist named "Corey Kent"
- **THEN** "Corey Kent" is matched to that artist, and the event shows a "Corey Kent" button

#### Scenario: Another band, not an occasion
- **WHEN** "Dark Star" is matched, and an event names "Dark Star Orchestra"
- **THEN** the event doesn't get the "Dark Star" button, since "Orchestra" doesn't name an occasion

### Requirement: Only Spotify IDs are stored, and only while needed
For each name, the site SHALL store only the normalized name, a status, a Spotify artist ID when there is one, how the link was set (automatic or by an editor), and when it was last checked. It SHALL NOT store any artist name, image, genre, popularity, follower count or other data returned by Spotify.

Automatic matched, ambiguous and not-found results older than 30 days SHALL be searched again on the next run. A link whose name hasn't appeared on any upcoming approved event for 30 days SHALL be deleted on the next run, whether it was set automatically or by an editor.

#### Scenario: Stale automatic match re-checked
- **WHEN** a name was matched automatically 31 days ago and still appears on an upcoming event
- **THEN** the next run searches Spotify for it again, and updates its status, ID and check date

#### Scenario: Link no longer needed
- **WHEN** a name's last upcoming event passed 31 days ago
- **THEN** the next run deletes its link

#### Scenario: Nothing else stored
- **WHEN** a name is matched
- **THEN** the stored row holds the normalized name, status, ID, source and check date, and no other value from Spotify's response

### Requirement: Editors can set or override a match in the admin
The admin SHALL list Spotify links with filters by status and source. An editor SHALL be able to:
- paste a Spotify artist URL or URI, which sets the name to matched with that ID;
- mark a name as "no Spotify artist".

Either action SHALL record the link as set by an editor. Later runs SHALL NOT search for, change or re-check names an editor has set, except to delete them under the 30-day rule. Saving a link SHALL re-render the stored HTML of the upcoming events that name it.

#### Scenario: Editor fixes a wrong match
- **WHEN** an editor pastes `https://open.spotify.com/artist/abc123?si=x` for "Epicenter"
- **THEN** the link is matched with ID `abc123`, set by an editor, and the upcoming Epicenter events show the button for `abc123`

#### Scenario: Editor marks no artist
- **WHEN** an editor marks "Organization Night" as having no Spotify artist
- **THEN** no button shows for it, and later runs don't search for it

#### Scenario: Invalid URL rejected
- **WHEN** an editor pastes `https://example.com/band`
- **THEN** the admin shows a validation error, and the link is unchanged

### Requirement: The listing offers a click-to-play Spotify player for matched artists
For each upcoming event, the listing SHALL show a play button for each of its names that is matched, in the order the names appear, in a row of their own below the event's text, outside the text with its ICAL, GCAL and MAP links. Each button SHALL show the artist name as written on the event and a Spotify mark. It SHALL be a link to `https://open.spotify.com/artist/<id>`.

With JavaScript, clicking the button SHALL instead insert Spotify's embedded artist player (`https://open.spotify.com/embed/artist/<id>`) below the row of buttons, and clicking it again SHALL remove the player. No Spotify iframe or script SHALL load before a click. At most one player SHALL be open at a time: opening another closes the previous one.

Names that are ambiguous, not found or marked "no Spotify artist" SHALL show no button. When Spotify isn't configured, no buttons SHALL show.

#### Scenario: Button for a matched artist
- **WHEN** an upcoming event names "SHEBAD" and "Psymon Spine", and only Psymon Spine is matched
- **THEN** the event shows one button, labelled "Psymon Spine", linking to that artist's Spotify page, in a row below the event's text rather than inside it

#### Scenario: No player before a click
- **WHEN** the homepage loads with several matched artists
- **THEN** the page contains no iframe from `open.spotify.com`

#### Scenario: Click opens the player
- **WHEN** a visitor clicks the Psymon Spine button
- **THEN** a Spotify embed iframe for that artist ID appears below the event's buttons

#### Scenario: One player at a time
- **WHEN** a player is open and the visitor clicks another artist's button
- **THEN** the first player is removed, and the second appears

#### Scenario: Without JavaScript
- **WHEN** JavaScript is off and the visitor clicks a button
- **THEN** the browser follows the link to the artist's page on Spotify

### Requirement: Spotify requests are throttled and recover from rate limits
The command SHALL space its Spotify requests at least 2 seconds apart. On a 429 it SHALL wait as long as the `Retry-After` header says, backing off exponentially, for at most three tries for the same request. When a request still fails, or fails with another error, the command SHALL leave that name's link unchanged, count the failure, and continue with the other names.

When a `Retry-After` asks for more than 60 seconds, the app is blocked for a long time. The command SHALL then stop searching without waiting, and keep and re-render what it found so far. The next run SHALL carry on with the names still due.

It SHALL record in its job summary the counts of searched, matched, ambiguous, not-found, deleted and failed names, and of names left for the next run.

#### Scenario: Rate limited then succeeds
- **WHEN** a search gets 429 with `Retry-After: 3`, and then succeeds
- **THEN** the command waits at least 3 seconds, then records the result

#### Scenario: Persistent failure
- **WHEN** a search fails three times with 429
- **THEN** that name's existing link is unchanged, the failure is counted, and the remaining names are still searched

#### Scenario: Blocked for hours
- **WHEN** a search gets 429 with `Retry-After: 85212`, after one name was matched in the same run
- **THEN** the command doesn't wait, makes no further request, keeps and re-renders the match it found, and reports the names left for the next run

#### Scenario: Next run carries on
- **WHEN** the run after a block starts, and one of two names was matched before the block
- **THEN** only the other name is searched

#### Scenario: Job summary
- **WHEN** a run searches 10 names, matching 6, finding 1 ambiguous and 2 not found, with 1 failure, and deletes 3 stale links
- **THEN** the job run's summary reports those counts, and 0 names left for the next run
