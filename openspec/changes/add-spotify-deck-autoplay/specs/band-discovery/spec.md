## RENAMED Requirements

- FROM: `### Requirement: Apple Music and Spotify cards load ready`
- TO: `### Requirement: Spotify cards are asked to start, and Apple Music cards load ready`

## MODIFIED Requirements

### Requirement: The top card starts playing after a visitor's action
Browsers allow sound to start by itself only after the visitor has acted on the page, so the first card SHALL wait for one: until the visitor has pressed a start control, the deck SHALL load no player and no Spotify script. The start control SHALL be laid over a placeholder, which SHALL be removed with it when the player loads. The placeholder is the first card's video thumbnail (top card only) or, when there is none or the design's open question 10 does not allow it, a plain dark box.

#### Scenario: Nothing plays before the visitor acts
- **WHEN** a visitor opens `/discover`
- **THEN** a start control is shown, and no YouTube, Apple Music or Spotify player, and no Spotify iFrame API script, is requested

#### Scenario: Start sits over the video thumbnail
- **WHEN** a visitor opens `/discover` and the first card is matched on YouTube with a video
- **THEN** the start control is shown over that video's thumbnail, and pressing it removes the thumbnail and the control and loads the player, so nothing is ever over the player

#### Scenario: Thumbnail for the top card only
- **WHEN** a visitor opens `/discover` with several YouTube-matched cards
- **THEN** only the top card's thumbnail is requested

#### Scenario: No thumbnail to show
- **WHEN** a visitor opens `/discover` and the first card has no YouTube video (Apple Music or Spotify only, or a channel match)
- **THEN** the start control is shown on a plain dark box

#### Scenario: Start begins the first card
- **WHEN** the visitor presses the start control and the first card is matched on YouTube
- **THEN** the YouTube player is loaded asking to start playing, and the hint and controls appear

#### Scenario: Start gates any service
- **WHEN** the first card is matched on Spotify only and the visitor presses Start
- **THEN** its Spotify player is loaded and asked to start playing, and the hint and controls appear

### Requirement: Each later card starts by itself
After the start control, each card that comes to the top because of a swipe, a button or an arrow key SHALL load its player asking the service to start playing. For YouTube, the player SHALL be loaded with `autoplay=1` and an `allow` that includes autoplay. For Spotify and Apple Music, see "Spotify cards are asked to start, and Apple Music cards load ready". Nothing SHALL be drawn over the player, and the sound of a passed or added card SHALL stop when its player is removed.

#### Scenario: Next card starts by itself
- **WHEN** the visitor skips a card and the next is matched on YouTube
- **THEN** the next card's YouTube player is loaded asking to start playing, and the passed card's player is gone

#### Scenario: A service that cannot be started
- **WHEN** the next card is matched on Apple Music only
- **THEN** its player is loaded ready, not started, with its own play control

#### Scenario: After saving
- **WHEN** the visitor saves shows in the picker
- **THEN** the next card's player starts as after a skip

#### Scenario: Keyboard
- **WHEN** the visitor starts the deck and moves through it with the arrow keys
- **THEN** each new top card's player is loaded asking to start playing

### Requirement: Spotify cards are asked to start, and Apple Music cards load ready
After the start control, a card matched on Spotify (and not YouTube) SHALL be loaded with Spotify's iFrame API controller for the artist, which SHALL be asked to `play()` once ready. The iFrame API script SHALL be loaded only in the deck, only after the start control, and at most once. If the script can't be loaded, the card SHALL get the plain Spotify embed, ready with its own play control; if the browser doesn't start it, it SHALL stay as loaded, with nothing drawn over it. Passing or adding the card SHALL destroy its controller, stopping its sound. Apple Music cards SHALL load ready, with their own play control, as Apple documents no way to start them.

#### Scenario: Ready, not started
- **WHEN** a card matched on Apple Music only comes to the top
- **THEN** its player is loaded without being started, with its own play control

#### Scenario: A Spotify card is asked to start
- **WHEN** the visitor skips a card and the next is matched on Spotify only
- **THEN** the iFrame API script is loaded, a controller is created for that artist's URI, and `play()` is called once it's ready

#### Scenario: The script once
- **WHEN** two Spotify cards come to the top one after the other
- **THEN** the iFrame API script is requested once

#### Scenario: The script can't be loaded
- **WHEN** the iFrame API script fails to load
- **THEN** the card gets the plain Spotify embed, ready with its own play control

#### Scenario: Sound stops when the card leaves
- **WHEN** a playing Spotify card is skipped
- **THEN** its controller is destroyed, and the next card's player loads

#### Scenario: The listing stays click-to-play
- **WHEN** a visitor presses a Spotify button in the events listing
- **THEN** the plain Spotify embed is shown, not started, and no iFrame API script is requested
