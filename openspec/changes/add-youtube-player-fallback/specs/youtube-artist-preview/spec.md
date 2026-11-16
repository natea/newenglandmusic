## RENAMED Requirements

- FROM: `### Requirement: Links are refreshed within 30 days and expire like the other links`
- TO: `### Requirement: Links are re-checked for playability and expire like the other links`

## MODIFIED Requirements

### Requirement: Links are re-checked for playability and expire like the other links
A link SHALL store:
- the normalized name, its status and its evidence;
- the YouTube channel ID and video ID;
- how it was set (automatically or by an editor);
- when it was last checked, and when an upcoming event last named it.

It SHALL NOT store any other YouTube data, such as titles, descriptions, thumbnails or counts.

A video SHALL count as playable only when it may be embedded, is public, has finished processing, isn't blocked in the United States, and isn't age-restricted. Every matched link with a video checked more than 7 days ago, and every channel-only link checked more than 30 days ago, an editor's included, SHALL have its video, or else its channel, re-read through the API. When the video is gone or no longer playable, or the channel is gone, an automatic link SHALL be re-matched, and an editor's SHALL lose its button until an editor fixes it. Links whose name no upcoming approved event has named for 30 days SHALL be deleted. Changing a link's status, channel or video SHALL re-render the stored HTML of the upcoming events that name it.

#### Scenario: Refresh keeps a live video
- **WHEN** a matched link was checked 8 days ago and its video is still playable
- **THEN** the next run updates its check date only

#### Scenario: Video removed
- **WHEN** a refresh finds an automatic link's video deleted
- **THEN** the link is matched again from scratch, and its events are re-rendered

#### Scenario: Link no longer needed
- **WHEN** a name's last upcoming event passed 31 days ago
- **THEN** the next run deletes its link

#### Scenario: Not playable in the US
- **WHEN** a refresh finds an automatic link's video private, still processing, blocked in the US, or age-restricted
- **THEN** the link is matched again, as for a removed video

### Requirement: The listing offers a click-to-play YouTube player for matched artists
When `YOUTUBE_PREVIEWS` is on, each upcoming event SHALL show a YouTube button for each of its matched names. The button SHALL:
- sit in the same row as the Spotify and Apple Music buttons;
- show the artist name as written on the event and a YouTube mark;
- be a link to the video (`https://www.youtube.com/watch?v=<video id>`), or, for a channel-only match, to the channel (`https://www.youtube.com/channel/<channel id>`).

With JavaScript:
- clicking the button SHALL instead insert YouTube's own embedded player below the row, built with YouTube's IFrame Player API on the `youtube-nocookie.com` host, followed by a "More by <artist name> on YouTube" link to the channel;
  - for a video, the player SHALL play `<video id>`;
  - for a channel-only match, it SHALL play the channel's full-length uploads playlist, `UULF<channel id without its "UC">`;
- the player SHALL be 16:9, as wide as the row, and at least 200 px wide and tall;
- nothing SHALL be drawn over it, and it SHALL NOT autoplay, except that the band discovery deck MAY ask its player to start when the visitor has just acted on that card;
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
- **THEN** a YouTube player for `abc123DEF45` on `youtube-nocookie.com` appears below the row, at least 200 px wide and tall, followed by a "More by … on YouTube" link

#### Scenario: Channel-only match plays its uploads
- **WHEN** a visitor clicks the button for Dinosaur Jr., matched to channel `UCfo74Lcf9bcQJd2MMq-XBzw` with no video
- **THEN** the player plays the playlist `UULFfo74Lcf9bcQJd2MMq-XBzw`, the channel's full-length uploads

#### Scenario: One player across services
- **WHEN** an Apple Music player is open and the visitor clicks a YouTube button
- **THEN** the Apple player is removed, and the YouTube player appears

#### Scenario: Switched off
- **WHEN** `YOUTUBE_PREVIEWS` is off
- **THEN** no YouTube buttons render, even for matched artists

## ADDED Requirements

### Requirement: A YouTube player that won't play is replaced
When YouTube's player reports that it can't play its video or playlist (removed, private, not embeddable, or unplayable in the browser), the page SHALL remove the player. In a listing, it SHALL show in its place a line saying YouTube won't play it here, with the act's other players from the same row (Apple Music, Spotify, Bandcamp) and a "Watch on YouTube" link to the video or channel. In the discovery deck, the card SHALL load its next player in the deck's order instead, or show the "Watch on YouTube" line when it has none. When YouTube's IFrame API script can't be loaded, the player SHALL be YouTube's plain embedded player, as before.

#### Scenario: A dead video in a listing
- **WHEN** a visitor opens the YouTube player for Tune-Yards and YouTube reports the video can't be played
- **THEN** the player is replaced by a line offering Tune-Yards' Spotify and Apple Music players and "Watch on YouTube"

#### Scenario: A dead video in the deck
- **WHEN** a deck card's YouTube player reports it can't play, and the act has an Apple Music player
- **THEN** the card loads the Apple Music player in its place

#### Scenario: Nothing else to play
- **WHEN** an act's only player is YouTube's and it reports it can't play
- **THEN** a "Watch on YouTube" link replaces it

#### Scenario: The API script doesn't load
- **WHEN** YouTube's IFrame API script fails to load
- **THEN** the button opens YouTube's plain embedded player, as before

### Requirement: A failed player is reported, and its link checked soon
When a YouTube player reports it can't play, the page SHALL send the video or channel ID to the site, without cookies or a form token. The site SHALL then make each matched link with that ID due for its next check, so the next `match_youtube_artists` run re-reads it. A report SHALL change nothing visitors see by itself; it SHALL accept only IDs in YouTube's formats, answer the same whatever it finds, and act at most once an hour for the same ID.

#### Scenario: A report makes a link due
- **WHEN** the page reports channel `UCeo49u1owRF9cHq8F8FiJGw`, which Tune-Yards' link has
- **THEN** that link is due for its next check, and its button is unchanged

#### Scenario: A malformed or repeated report
- **WHEN** a report carries an ID that isn't YouTube's format, or repeats an ID reported within the hour
- **THEN** the site answers the same way and changes nothing

### Requirement: A channel-only match looks for a song video on its own channel
For a link matched to a channel by ID with no video, `match_youtube_artists` SHALL search for the artist's top song as it does for a song match (Last.fm's top track, the same confirmation rules), and SHALL set the link's video to the first confirmed, playable result on that same channel, keeping the link's channel and evidence. A result on another channel SHALL NOT be used. These searches SHALL come after unmatched names, within the run's search limit, at most once every 30 days for a link.

#### Scenario: A song video on the channel
- **WHEN** Dinosaur Jr. is matched to its channel only, and the search for its top song finds that song's video on the same channel, playable
- **THEN** its link keeps the channel and the "wikidata" evidence, and gains that video

#### Scenario: A video on another channel
- **WHEN** the song search's only confirmed result is on a different channel
- **THEN** the link stays channel-only
