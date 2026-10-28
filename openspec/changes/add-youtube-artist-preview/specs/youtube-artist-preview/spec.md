## ADDED Requirements

### Requirement: Only artists already matched elsewhere are matched on YouTube
`match_youtube_artists` SHALL consider only names whose Spotify link, or Apple Music link, is matched. It SHALL never search YouTube for a name that is matched on neither. A name SHALL be considered once however many events name it.

When `YOUTUBE_API_KEY` isn't set, the command SHALL print that and exit successfully without making any request, since every match needs its channel or video checked through the API. `--dry-run` SHALL report what it would record without saving it.

#### Scenario: Not configured
- **WHEN** the command runs without `YOUTUBE_API_KEY`
- **THEN** it makes no request, saves nothing, and exits with status 0

#### Scenario: Unmatched name skipped
- **WHEN** "DJ Maltese" is ambiguous on Spotify and not found on Apple Music
- **THEN** the command makes no request for it and records nothing

#### Scenario: Dry run
- **WHEN** the command runs with `--dry-run`
- **THEN** it prints each name's would-be status, evidence and video or channel, and saves nothing

### Requirement: A channel linked by ID in Wikidata or MusicBrainz is a match
For each considered name, the command SHALL first look for a YouTube channel ID linked to the artist's Spotify or Apple Music ID:
- **in Wikidata:** an item whose Spotify artist ID (P1902) or Apple Music artist ID (P2850) equals the artist's, and which has a YouTube channel ID (P2397);
- **in MusicBrainz:** the artist linked to the artist's Spotify URL, and that artist's links to `youtube.com/channel/<id>`.

When exactly one channel ID is found, or exactly one is given by both sources, the name SHALL be matched to that channel, with the evidence recorded as "wikidata" or "musicbrainz". Otherwise, when the sources give several channels, the name SHALL be recorded as ambiguous. A channel SHALL be matched only once the API confirms it exists. Wikidata SHALL be queried in batches, and MusicBrainz no faster than one request a second, with the site's user agent.

MusicBrainz answers 503 when it's busy. Such a request SHALL be retried after 2, 4 and then 8 seconds. When it still fails, the rest of the run SHALL go without MusicBrainz, matching on Wikidata and the song search alone.

#### Scenario: Wikidata link
- **WHEN** Wikidata's item with Spotify ID `267VY6GX5LyU5c9M85ECZQ` has YouTube channel ID `UCfo74Lcf9bcQJd2MMq-XBzw`
- **THEN** Dinosaur Jr. is matched to that channel, with evidence "wikidata"

#### Scenario: A channel both sources give
- **WHEN** Wikidata gives channel A, and MusicBrainz gives channels A and B, for the same artist
- **THEN** the name is matched to channel A

#### Scenario: MusicBrainz busy
- **WHEN** MusicBrainz answers 503 to every try for one name
- **THEN** the run makes no more MusicBrainz requests, and still matches later names linked by Wikidata

#### Scenario: Sources disagree
- **WHEN** Wikidata gives one channel and MusicBrainz another for the same artist
- **THEN** the name is recorded as ambiguous, and no button shows

### Requirement: Otherwise, the artist's own recording of their top song is a match
When no channel is linked by ID and the name's Apple Music link has a top song, the command SHALL search YouTube for videos with "<artist name> <song name>", with a maximum of 10 results. It SHALL then read each result's channel title, title, description and embeddable status.

A result SHALL confirm the artist when all of these hold:
- **the channel is the artist's:** its normalized title equals the artist's normalized name, or the artist's normalized name followed by " - Topic";
- **it names the song:**
  - for a Topic channel, the description has the line "<song> · <artist>" and the album's name, both normalized;
  - otherwise, the video title contains the song's normalized name;
- **it can be embedded.**

The first confirming result SHALL be recorded as matched, with its video ID and channel ID. A Topic channel's video SHALL be preferred over the artist channel's. The evidence SHALL be recorded as "topic-song" or "channel-song". When no result confirms, the name SHALL be recorded as not found.

Names SHALL compare as normalized for Spotify. The song and album names SHALL be used only during the run, and SHALL NOT be stored.

#### Scenario: Topic channel recording
- **WHEN** a search for "The Ballroom Thieves Archers" returns a video from "The Ballroom Thieves - Topic" whose description reads "Provided to YouTube by …", "Archers · The Ballroom Thieves" and "A Wolf in the Doorway"
- **THEN** the name is matched to that video and channel, with evidence "topic-song"

#### Scenario: Same name, different band
- **WHEN** the only result from a channel titled "Epicenter" is titled "Epicenter - Live at the Fest", and the Apple top song is "Glass Hours"
- **THEN** the name is recorded as not found

#### Scenario: Cover or fan upload
- **WHEN** a result titled "The Ballroom Thieves - Archers (cover)" comes from a channel titled "guitarjoe"
- **THEN** it doesn't confirm the artist

#### Scenario: Not embeddable
- **WHEN** the only confirming video can't be embedded
- **THEN** the name is recorded as not found

#### Scenario: Spotify-only artist with no ID link
- **WHEN** a name is matched on Spotify only, and neither Wikidata nor MusicBrainz links a channel
- **THEN** the command makes no YouTube search for it, and records it as not found

### Requirement: Searches stay within YouTube's free daily quota
The command SHALL make at most `--limit` song searches per run, default 90. A search with its video lookup costs 101 of the free 10,000 daily units. Names not reached SHALL be left for the next run.

On a 403 with reason `quotaExceeded` or `dailyLimitExceeded`, it SHALL stop searching without retrying, keep and re-render what it found, and report the names left. On any other 403, or a 400 `keyInvalid`, Google has refused the key (a key restricted to websites is refused from a server). The command SHALL then stop at once, save nothing more, and fail, saying the key's API and application restriction need checking. On a 429 or 5xx it SHALL back off (1, 2, then 4 seconds), for at most three tries, then leave that name unchanged, count the failure, and continue. It SHALL record the counts of considered, searched, matched by each kind of evidence, ambiguous, not-found, refreshed, deleted and failed names in its job summary.

#### Scenario: Limit reached
- **WHEN** 120 names need a search and the limit is 90
- **THEN** 90 are searched, and the other 30 are left for the next run

#### Scenario: Key refused
- **WHEN** YouTube answers 403 `forbidden` to the first request
- **THEN** the command makes no further YouTube request, records nothing for the names left, and fails with a message about the key's restrictions

#### Scenario: Quota exhausted
- **WHEN** a search gets 403 `quotaExceeded` after one name was matched in the run
- **THEN** the command makes no further YouTube request, keeps and re-renders that match, and reports the names left

### Requirement: Links are refreshed within 30 days and expire like the other links
A link SHALL store:
- the normalized name, its status and its evidence;
- the YouTube channel ID and video ID;
- how it was set (automatically or by an editor);
- when it was last checked, and when an upcoming event last named it.

It SHALL NOT store any other YouTube data, such as titles, descriptions, thumbnails or counts.

Every matched link checked more than 30 days ago, an editor's included, SHALL have its video, or else its channel, re-read through the API. When the video is gone or no longer embeddable, or the channel is gone, an automatic link SHALL be re-matched, and an editor's SHALL lose its button until an editor fixes it. Links whose name no upcoming approved event has named for 30 days SHALL be deleted. Changing a link's status, channel or video SHALL re-render the stored HTML of the upcoming events that name it.

#### Scenario: Refresh keeps a live video
- **WHEN** a matched link was checked 31 days ago and its video is still embeddable
- **THEN** the next run updates its check date only

#### Scenario: Video removed
- **WHEN** a refresh finds an automatic link's video deleted
- **THEN** the link is matched again from scratch, and its events are re-rendered

#### Scenario: Link no longer needed
- **WHEN** a name's last upcoming event passed 31 days ago
- **THEN** the next run deletes its link

### Requirement: Editors can set or override a YouTube match
The admin SHALL list YouTube links, with filters by status, evidence and source. An editor SHALL be able to:
- paste a YouTube channel URL (`https://www.youtube.com/channel/UC…`), which matches the name to that channel;
- paste a video URL (`https://www.youtube.com/watch?v=…` or `https://youtu.be/…`), which matches the name to that video and its channel;
- mark a name as "no YouTube".

Either action SHALL record the link as set by an editor, with evidence "editor". Later runs SHALL NOT re-match an editor's link or change its channel or video. They SHALL only refresh it, and delete it under the 30-day rule. Saving a link SHALL re-render the stored HTML of the upcoming events that name it. An editor's match SHALL show its button even when the name isn't matched on Spotify or Apple Music.

#### Scenario: Editor pastes a video
- **WHEN** an editor pastes `https://youtu.be/dQw4w9WgXcQ` for a name
- **THEN** the link is matched to that video by an editor, and its events show the YouTube button

#### Scenario: Invalid link rejected
- **WHEN** an editor pastes `https://open.spotify.com/artist/abc123` as a YouTube link
- **THEN** the admin shows a validation error, and the link is unchanged

#### Scenario: Editor marks no YouTube
- **WHEN** an editor marks a name as having no YouTube
- **THEN** no YouTube button shows for it, and later runs don't match it

### Requirement: The listing offers a click-to-play YouTube player for matched artists
When `YOUTUBE_PREVIEWS` is on, each upcoming event SHALL show a YouTube button for each of its matched names. The button SHALL:
- sit in the same row as the Spotify and Apple Music buttons;
- show the artist name as written on the event and a YouTube mark;
- be a link to the video (`https://www.youtube.com/watch?v=<video id>`), or, for a channel-only match, to the channel (`https://www.youtube.com/channel/<channel id>`).

With JavaScript:
- clicking the button SHALL instead insert YouTube's own embedded player below the row, followed by a "More by <artist name> on YouTube" link to the channel;
  - for a video, the player SHALL be `https://www.youtube-nocookie.com/embed/<video id>`;
  - for a channel-only match, it SHALL be the channel's uploads playlist, `https://www.youtube-nocookie.com/embed/videoseries?list=UU<channel id without its "UC">`;
- the player SHALL be 16:9, as wide as the row, and at least 200 px wide and tall;
- nothing SHALL be drawn over it, and it SHALL NOT autoplay;
- clicking the button again SHALL remove the player and the link.

No YouTube iframe or script SHALL load before a click. At most one player, from any service, SHALL be open at a time.

#### Scenario: YouTube button beside the others
- **WHEN** an upcoming event names "The Ballroom Thieves", matched on Spotify, Apple Music and YouTube
- **THEN** its row shows all three buttons for The Ballroom Thieves

#### Scenario: No player before a click
- **WHEN** the homepage loads with several YouTube-matched artists
- **THEN** the page contains no iframe or script from `youtube.com` or `youtube-nocookie.com`

#### Scenario: Click opens the video
- **WHEN** a visitor clicks the YouTube button for a name matched to video `abc123DEF45`
- **THEN** an iframe with the src `https://www.youtube-nocookie.com/embed/abc123DEF45` appears below the row, at least 200 px wide and tall, followed by a "More by … on YouTube" link

#### Scenario: Channel-only match plays its uploads
- **WHEN** a visitor clicks the button for Dinosaur Jr., matched to channel `UCfo74Lcf9bcQJd2MMq-XBzw` with no video
- **THEN** the iframe's src is `https://www.youtube-nocookie.com/embed/videoseries?list=UUfo74Lcf9bcQJd2MMq-XBzw`

#### Scenario: One player across services
- **WHEN** an Apple Music player is open and the visitor clicks a YouTube button
- **THEN** the Apple player is removed, and the YouTube player appears

#### Scenario: Switched off
- **WHEN** `YOUTUBE_PREVIEWS` is off
- **THEN** no YouTube buttons render, even for matched artists

### Requirement: The API key stays secret
The site SHALL send `YOUTUBE_API_KEY` only in the `X-goog-api-key` header of server-side requests. The key SHALL never appear in a URL, a page, a log line or an error message.

#### Scenario: Key out of URLs and errors
- **WHEN** the client makes a request, and when a request fails with 400
- **THEN** the request URL holds no key, and neither the error message nor the listing's HTML contains it

### Requirement: The site discloses its use of YouTube API Services
The site SHALL have a `/privacy` page, linked from every page's footer, that:
- says the site uses YouTube API Services;
- links to the Google Privacy Policy (`https://policies.google.com/privacy`);
- links to YouTube's Terms of Service (`https://www.youtube.com/t/terms`), and says that by using the YouTube player, visitors agree to them;
- says what the site stores in cookies (saved shows) and that YouTube's player, once a visitor opens it, is served by YouTube.

#### Scenario: Privacy page
- **WHEN** a visitor opens `/privacy`
- **THEN** it names YouTube API Services, and links to the Google Privacy Policy and YouTube's Terms of Service

#### Scenario: Footer link
- **WHEN** any page of the listing renders
- **THEN** its footer links to `/privacy`
