## Purpose

Lets visitors who use Apple Music sample an act from the events listing in Apple's own player, alongside the Spotify buttons. Each artist name is linked to its Apple Music artist and most popular song only where the match is clear.

## ADDED Requirements

### Requirement: Artist names are matched to Apple Music artists on an unambiguous exact match
`match_apple_music_artists` SHALL collect the artist names of upcoming approved music events, using the same name extraction as the Spotify matching. For each name that has no link yet, or whose automatic link is due for a refresh, it SHALL search the Apple Music catalog's US storefront for artists, with a limit of 10.

It SHALL record each name as one of:
- **matched**, with the Apple Music artist ID, when exactly one result has the same normalized name;
- **ambiguous**, when more than one result does;
- **not found**, when none does.

Normalized names SHALL compare as they do for Spotify. A name SHALL be searched once however many events name it. When the Apple Music credentials aren't all set, the command SHALL print that and exit successfully without making any request. `--dry-run` SHALL report what it would record without saving it.

#### Scenario: Unique exact match
- **WHEN** a search for "The Ballroom Thieves" returns one artist named "The Ballroom Thieves"
- **THEN** the name is recorded as matched, with that artist's ID

#### Scenario: Two artists with the same name
- **WHEN** a search for "Epicenter" returns two artists, each named "Epicenter"
- **THEN** the name is recorded as ambiguous, with no artist ID

#### Scenario: No exact match
- **WHEN** a search for "Haven's Den" returns only "Haven" and "The Den"
- **THEN** the name is recorded as not found

#### Scenario: Not configured
- **WHEN** the command runs without `APPLE_MUSIC_PRIVATE_KEY`
- **THEN** it makes no request, saves nothing, and exits with status 0

#### Scenario: Dry run
- **WHEN** the command runs with `--dry-run`
- **THEN** it prints each name's would-be status and top song, and saves nothing

### Requirement: A matched artist's top song is the first in Apple's top songs
For each matched artist, the command SHALL request the artist's `top-songs` view, and record the first song's ID and its album's ID. When the artist has no top songs, the link SHALL stay matched with no song, and the listing SHALL show no Apple button for it.

#### Scenario: Top song recorded
- **WHEN** the top songs of The Ballroom Thieves begin with "Archers" (song 964625539, on album 964625535)
- **THEN** the link records song `964625539` and album `964625535`

#### Scenario: No top songs
- **WHEN** an artist's top-songs view is empty
- **THEN** the link is matched with no song, and no Apple button shows for the artist

### Requirement: Links are refreshed and expire like the Spotify links
A link SHALL store:
- the normalized name and its status;
- the Apple Music artist ID, and the top song's ID and album ID;
- how it was set (automatically or by an editor);
- when it was last checked, and when an upcoming event last named it.

It SHALL NOT store any other catalog data, such as names, artwork or preview URLs.

The command SHALL search again for automatic links checked more than 30 days ago, and SHALL re-read the top song of every matched link checked more than 30 days ago, an editor's included. It SHALL delete links whose name no upcoming approved event has named for 30 days. Changing a link's status, artist or song SHALL re-render the stored HTML of the upcoming events that name it.

#### Scenario: Refresh after 30 days
- **WHEN** an automatic link was checked 31 days ago and still appears on an upcoming event
- **THEN** the next run searches for it again, re-reads its top song, and updates its artist, song and check date

#### Scenario: Editor's match keeps its artist but gets a new top song
- **WHEN** an editor's link was checked 31 days ago, and the artist's top song has changed
- **THEN** the next run keeps the editor's artist, and records the new top song

#### Scenario: Link no longer needed
- **WHEN** a name's last upcoming event passed 31 days ago
- **THEN** the next run deletes its link

#### Scenario: Changed song re-rendered
- **WHEN** a refresh records a different top song for an artist on two upcoming events
- **THEN** both events' stored HTML uses the new song and album IDs

### Requirement: Editors can set or override an Apple Music match
The admin SHALL list Apple Music links, with filters by status and source. An editor SHALL be able to:
- paste an Apple Music artist URL, such as `https://music.apple.com/us/artist/the-ballroom-thieves/489634654`, which sets the name to matched with that artist ID, and looks up its top song;
- mark a name as "no Apple Music artist".

Either action SHALL record the link as set by an editor. Later runs SHALL NOT search for an editor's link or change its artist. They SHALL only refresh its top song and delete it under the 30-day rule. Saving a link SHALL re-render the stored HTML of the upcoming events that name it.

#### Scenario: Editor sets a match
- **WHEN** an editor pastes `https://music.apple.com/us/artist/the-ballroom-thieves/489634654` for "Ballroom Thieves"
- **THEN** the link is matched to artist `489634654` and set by an editor, its top song is looked up, and its events show the Apple button

#### Scenario: Invalid link rejected
- **WHEN** an editor pastes `https://open.spotify.com/artist/abc123` as an Apple Music link
- **THEN** the admin shows a validation error, and the link is unchanged

#### Scenario: Editor marks no artist
- **WHEN** an editor marks "Organization Night" as having no Apple Music artist
- **THEN** no Apple button shows for it, and later runs don't search for it

### Requirement: The listing offers a click-to-play Apple Music player for matched artists
When the Apple Music credentials are set and `APPLE_MUSIC_PREVIEWS` is on, each upcoming event SHALL show an Apple Music button for each of its names matched with a top song. The buttons SHALL sit in the same row as the Spotify buttons, below the event's text and outside it. Each button SHALL show the artist name as written on the event and an Apple Music mark. It SHALL be a link to the artist's Apple Music page, `https://music.apple.com/us/artist/<artist id>`.

With JavaScript:
- clicking the button SHALL instead insert Apple's embedded player for the top song (`https://embed.music.apple.com/us/album/<album id>?i=<song id>`) below the row, followed by a "More by <artist name> on Apple Music" link to the artist's page;
- clicking it again SHALL remove the player and the link.

No Apple iframe or script SHALL load before a click. At most one player, Apple or Spotify, SHALL be open at a time.

#### Scenario: Apple button beside the Spotify button
- **WHEN** an upcoming event names "The Ballroom Thieves", which is matched on both Spotify and Apple Music
- **THEN** its row shows a Spotify button and an Apple Music button for The Ballroom Thieves, and the Apple button links to `https://music.apple.com/us/artist/489634654`

#### Scenario: Apple only
- **WHEN** an artist is matched on Apple Music but not on Spotify
- **THEN** the event's row shows only the Apple Music button for that artist

#### Scenario: No player before a click
- **WHEN** the homepage loads with several Apple-matched artists
- **THEN** the page contains no iframe from `embed.music.apple.com`

#### Scenario: Click opens the top song and the artist link
- **WHEN** a visitor clicks the Apple button for The Ballroom Thieves
- **THEN** an iframe with the src `https://embed.music.apple.com/us/album/964625535?i=964625539` appears below the row, followed by a "More by The Ballroom Thieves on Apple Music" link to the artist's page

#### Scenario: One player across services
- **WHEN** a Spotify player is open and the visitor clicks an Apple button
- **THEN** the Spotify player is removed, and the Apple player appears

#### Scenario: Switched off
- **WHEN** `APPLE_MUSIC_PREVIEWS` is off
- **THEN** no Apple buttons render, even for matched artists

### Requirement: The developer token is signed on the server and kept secret
The site SHALL sign its own developer token from the configured team ID, key ID and private key: an ES256 JWT, with the team ID as issuer and the key ID in its header, expiring at most one hour after it's issued. Its issue time SHALL be backdated by a minute, so that a server whose clock is slightly behind doesn't see it as issued in the future. It SHALL send the token only in the `Authorization` header of server-side requests. The private key and the token SHALL never appear in a page, a URL, a log line or an error message.

#### Scenario: Token signed correctly
- **WHEN** the client makes a request
- **THEN** its `Authorization` header holds a bearer JWT that verifies against the key's public half with ES256, with `iss` set to the team ID, `kid` set to the key ID, and `exp` at most one hour after `iat`

#### Scenario: Secrets stay out of pages and errors
- **WHEN** the listing renders, and when a request fails with 401
- **THEN** neither the HTML nor the error message contains the private key or the token

### Requirement: Apple's rate limits are respected
The command SHALL space its requests at least 0.5 seconds apart. On a 429 it SHALL wait as long as the `Retry-After` header says, or else back off exponentially (1, 2, then 4 seconds), for at most three tries for the same request. When a request still fails, or fails with another error, the command SHALL leave that name's link unchanged, count the failure, and continue. On a 401, it SHALL retry the request with the same token, after 2, 4, 8 and then 16 seconds, for at most five tries, since Apple rejects about one valid request in ten, sometimes several in a row. A 401 on all five tries means the credentials are wrong, and it SHALL stop the run. When a `Retry-After` asks for more than 60 seconds, it SHALL stop searching without waiting, keep and re-render what it found, and leave the remaining names for the next run. It SHALL record the counts of searched, matched, ambiguous, not-found, deleted and failed names in its job summary.

#### Scenario: Rate limited then succeeds
- **WHEN** a search gets 429 with `Retry-After: 3`, and then succeeds
- **THEN** the command waits at least 3 seconds, then records the result

#### Scenario: Persistent failure
- **WHEN** a search fails three times with 429
- **THEN** that name's link is unchanged, the failure is counted, and the remaining names are still searched

#### Scenario: Blocked for hours
- **WHEN** a search gets 429 with `Retry-After: 86400`, after one name was matched in the same run
- **THEN** the command doesn't wait, makes no further request, keeps and re-renders the match it found, and reports the names left for the next run

#### Scenario: Spurious rejection
- **WHEN** Apple answers 401 four times, then 200
- **THEN** the request succeeds with the same token, and the run carries on

#### Scenario: Bad credentials stop the run
- **WHEN** Apple answers 401 to a request and to all four of its retries
- **THEN** the command stops searching, saves nothing more, and reports that the Apple Music credentials were rejected
