## Purpose

Uses Last.fm and MusicBrainz, behind the scenes, as evidence of which artist an event's name means: to settle names that several Spotify or Apple Music artists share, and to give names matched only on Spotify a song to confirm on YouTube. Nothing from Last.fm is shown or kept.

## ADDED Requirements

### Requirement: Ambiguous names are resolved on Last.fm and MusicBrainz evidence
`resolve_artists_with_lastfm` SHALL consider each automatic Spotify or Apple Music link that is ambiguous and named by an upcoming approved music event, and was not considered in the last 30 days. For each, it SHALL read the name's Last.fm page, with no autocorrection, for its MusicBrainz ID, bio summary and listener count. When the page has a MusicBrainz ID, it SHALL look that artist up on MusicBrainz, for its name, its area and begin area, and its links to Spotify and Apple Music artist pages.

It SHALL match the link to the linked artist (the Spotify link to the Spotify artist, the Apple Music link to the Apple Music artist) only when all of these hold:
- the MusicBrainz artist's normalized name equals the link's name;
- MusicBrainz links exactly one artist on that service;
- the artist is **local** or **dominant**:
  - **local:** the MusicBrainz area or begin area is a US state where the site has a venue, or is part of one, following MusicBrainz's "part of" links from a city or county up to the state, at most five steps. A town's name SHALL NOT decide this, since many towns share names with places elsewhere, such as Windsor, Ontario and Windsor, Connecticut. Or: the Last.fm bio names such a state, in full or as "<town>, <state code>", and doesn't say several acts share the name. A town named alone in a bio SHALL NOT count, since many town names are also surnames or words;
  - **dominant:** the Last.fm page has at least 100,000 listeners, and its bio doesn't say several acts share the name ("There are at least two…", "There are several…", "There are 2…", or a numbered list of acts).

Otherwise the link SHALL stay ambiguous. A matched link SHALL be recorded with the source "evidence". An Apple Music link matched this way SHALL get its top song looked up, as an editor's does. Matching a link SHALL re-render the stored HTML of the upcoming events that name it. `--dry-run` SHALL report what would be matched and why, and save nothing.

#### Scenario: Local act
- **WHEN** "DJ Lucas" is ambiguous on Spotify, its Last.fm page has a MusicBrainz ID whose artist is named "DJ Lucas", has the area "Massachusetts", and links one Spotify artist, and the site has venues in MA
- **THEN** the Spotify link is matched to that artist, with source "evidence"

#### Scenario: Dominant touring act
- **WHEN** "Bonobo" is ambiguous on Spotify, its Last.fm page has 2,121,800 listeners and a bio about one act, and MusicBrainz links its ID to one Spotify artist
- **THEN** the Spotify link is matched to that artist, even though its area, Brighton, isn't a place the site covers

#### Scenario: Shared name flagged on Last.fm
- **WHEN** the Last.fm bio for "Dead Weight" begins "There are several bands called Dead Weight", and MusicBrainz's area for its ID is "St Albans"
- **THEN** the link stays ambiguous

#### Scenario: Shared page's bio names a covered state
- **WHEN** the Last.fm bio for "Alien" lists "1) - Alien is a Swedish band…" and "2) … a rapper from Western Massachusetts", and MusicBrainz's area for its ID is "Sweden"
- **THEN** the link stays ambiguous

#### Scenario: A same-named town in another country
- **WHEN** MusicBrainz's begin area for "The Blue Stones" is Windsor, which is part of Essex County, which is part of Ontario, and the site has a venue in Windsor, CT
- **THEN** it doesn't count as local

#### Scenario: A venue town named alone in a bio
- **WHEN** a small act's bio mentions "drummer Hamden Jones", and the site has a venue in Hamden
- **THEN** it doesn't count as local

#### Scenario: Small act from elsewhere
- **WHEN** a Last.fm page has 4,800 listeners, and the MusicBrainz artist's area is "Germany"
- **THEN** the link stays ambiguous

#### Scenario: No MusicBrainz ID or link
- **WHEN** the Last.fm page has no MusicBrainz ID, or MusicBrainz links no artist on that service
- **THEN** the link stays ambiguous

#### Scenario: Different name on MusicBrainz
- **WHEN** the MusicBrainz artist for the page's ID is named "Bars of Gold" while the link's name is "Bars"
- **THEN** the link stays ambiguous

#### Scenario: Apple Music link resolved
- **WHEN** an ambiguous Apple Music link is resolved to artist 489634654
- **THEN** it is matched with source "evidence", its top song is looked up, and its events show the Apple Music button

#### Scenario: Recently considered
- **WHEN** an ambiguous link was considered 10 days ago and stayed ambiguous
- **THEN** the run doesn't consider it again

### Requirement: Evidence links are kept like an editor's
The Spotify and Apple Music matching SHALL NOT search for a link with the source "evidence", or change its artist. They SHALL delete it under their 30-day rule, and Apple Music's SHALL refresh its top song, as for an editor's link. `resolve_artists_with_lastfm` SHALL re-check an evidence link 30 days after it was matched. When the evidence no longer holds, it SHALL set the link back to ambiguous with the source "automatic", and re-render its events. An editor SHALL be able to override an evidence link in the admin as they would an automatic one. `resolve_artists_with_lastfm --revert` SHALL set every evidence link back to ambiguous, with source "automatic", and re-render their events.

#### Scenario: Spotify matching leaves it alone
- **WHEN** an evidence link is 31 days old, and `match_spotify_artists` runs
- **THEN** it doesn't search for the name, and the link keeps its artist

#### Scenario: Revert
- **WHEN** the command runs with `--revert` and three links have the source "evidence"
- **THEN** all three are ambiguous with source "automatic", and their events lose their buttons

#### Scenario: Evidence gone
- **WHEN** a re-check finds that MusicBrainz no longer links the artist
- **THEN** the link is ambiguous again, with source "automatic", and its events lose its button

### Requirement: Nothing from Last.fm is shown or stored
No page SHALL show text, tags, numbers, images or links from Last.fm. Links SHALL store no Last.fm or MusicBrainz data: only the Spotify, Apple Music and YouTube IDs they store already, with the source, the status, and when they were checked. The run SHALL keep Last.fm data in memory only.

#### Scenario: Nothing kept
- **WHEN** a link is resolved on a bio that names Massachusetts
- **THEN** no stored field holds the bio, its listener count or its MusicBrainz ID

### Requirement: The Last.fm client is polite and keeps its key out of logs
The client SHALL send at most two requests a second, with the site's user agent, and the key as the `api_key` parameter, which is the only way Last.fm accepts it. Error messages and printed output SHALL NOT contain the key or a request URL. On Last.fm error 29 (rate limit exceeded), or 26 (key suspended), the run SHALL stop at once, keep and re-render what it found, and report the names left. Error 6 (no such artist) SHALL count as no evidence. When `LASTFM_API_KEY` isn't set, the command SHALL print that and exit successfully without any request. A MusicBrainz 503 that persists after its retries SHALL stop the run's MusicBrainz lookups, leaving the remaining names for the next run.

#### Scenario: Rate limited
- **WHEN** Last.fm answers error 29 after one name was resolved
- **THEN** the run makes no further request, keeps and re-renders that name, and reports the rest as left

#### Scenario: Key out of errors
- **WHEN** a request fails
- **THEN** the error message and the output contain neither the key nor the request URL

#### Scenario: Not configured
- **WHEN** the command runs without `LASTFM_API_KEY`
- **THEN** it makes no request, saves nothing, and exits with status 0
