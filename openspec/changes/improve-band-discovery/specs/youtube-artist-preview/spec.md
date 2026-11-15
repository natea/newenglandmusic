## MODIFIED Requirements

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
- nothing SHALL be drawn over it, and it SHALL NOT autoplay, except that the band discovery deck MAY ask its player to start (`autoplay=1`) when the visitor has just acted on that page (see the `band-discovery` capability); the listings' players SHALL NOT;
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

#### Scenario: The deck's player may autoplay after a visitor action
- **WHEN** a visitor on `/discover` has pressed Start or swiped to a card matched on YouTube
- **THEN** the player's src is the same `youtube-nocookie.com` embed with `autoplay=1` added, and nothing is drawn over it

#### Scenario: The listing's player still does not autoplay
- **WHEN** a visitor clicks a YouTube button on the homepage
- **THEN** the iframe's src has no `autoplay` parameter
