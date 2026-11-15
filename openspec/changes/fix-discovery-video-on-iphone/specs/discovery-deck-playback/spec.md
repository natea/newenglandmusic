## ADDED Requirements

### Requirement: The deck asks a YouTube video to start on iPhone after the visitor's action
On a phone running iOS (Chrome or Safari), a card whose best match is a YouTube video SHALL ask its player to start playing, by the route recorded in the design after the phone spike (task 1.2), when the card comes up because of the visitor's Start press, or later because of a swipe, button or arrow key. If iOS refuses, the next requirement's note shows.

#### Scenario: Start plays the first video on iPhone
- **WHEN** a visitor on an iOS browser presses Start and the first card is matched on a YouTube video
- **THEN** the card's YouTube player is loaded for the visitor's action and asked to play by the recorded route (the stub player is told to play), with no further tap from the visitor

#### Scenario: A later card plays on iPhone
- **WHEN** a visitor on an iOS browser skips, or saves shows from, a card and the next is matched on a YouTube video
- **THEN** the next card's player is loaded and asked to play by the same route (or, if the spike shows swipes do not count as a tap on iOS, shows the note as in the next requirement), and the passed card's player is gone

#### Scenario: Desktop is unchanged
- **WHEN** a visitor on desktop Chrome presses Start on a YouTube-matched first card
- **THEN** the player loads with exactly the address it has today (`autoplay=1&playsinline=1`, no `enablejsapi`), and no note is shown

### Requirement: The deck says when one tap on play is needed
On iOS, the deck SHALL watch the card's YouTube player through YouTube's IFrame Player API (loaded only after Start, from the deck's iPhone path), whichever route starts the video. When the video was asked to play and has not started after a short wait, the deck SHALL show a note by the player, outside it, saying to tap play. The note SHALL go as soon as the video plays, and SHALL NOT appear for cards on Apple Music or Spotify, which load ready.

#### Scenario: Phone refuses
- **WHEN** the YouTube player was asked to play and has not reported playing within the wait after the card came up
- **THEN** a "tap play to start" note shows beside the player, not over it

#### Scenario: Video starts
- **WHEN** the player reports playing, before or after the wait
- **THEN** no note shows, or the note is removed

#### Scenario: Ready cards
- **WHEN** the top card is matched on Apple Music or Spotify only
- **THEN** no "tap play" note shows

### Requirement: The listings and YouTube's player stay as they are
The listing's players SHALL NOT change or autoplay, nothing SHALL be drawn over YouTube's player, and a passed card's sound SHALL stop with its player.

#### Scenario: The listing is untouched
- **WHEN** a visitor opens the event listing and presses a YouTube button
- **THEN** the player appears with no `autoplay` in its address or its `allow`, and waits for the visitor to press play

### Requirement: Nothing loads from YouTube before Start
Before the visitor presses Start, the deck SHALL NOT load a YouTube player or any script from YouTube, as today, beyond the first card's thumbnail. The IFrame Player API script loads only after Start.

#### Scenario: Before Start
- **WHEN** a visitor opens `/discover` and has not pressed Start
- **THEN** no request goes to a YouTube embed address or script address
