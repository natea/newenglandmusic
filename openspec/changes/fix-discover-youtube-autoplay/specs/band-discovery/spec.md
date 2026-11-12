## ADDED Requirements

### Requirement: The top card's YouTube player is asked to play when it is ready
When the deck loads a YouTube player for the top card, the page SHALL listen to that player's messages (only from YouTube's embed addresses, and only from that card's frame), and when the player reports ready it SHALL send it the `playVideo` command, in addition to the `autoplay=1` in its address. It SHALL send nothing to a player that is not the top card's, and when a card leaves the top the page SHALL stop listening to its player and its player SHALL be removed.

#### Scenario: Ready player is told to play
- **WHEN** the top card's YouTube player reports that it is ready
- **THEN** the page sends that player `playVideo`

#### Scenario: A passed card is not told to play
- **WHEN** a visitor skips a card and the passed card's player reports ready afterwards
- **THEN** no `playVideo` is sent to it, and its player is gone

#### Scenario: A message from elsewhere is ignored
- **WHEN** a message that does not come from the top card's YouTube frame says "ready"
- **THEN** the page sends no command

### Requirement: A player that did not start says so beside itself
When the top card's YouTube player has not started playing after it was asked to, the page SHALL try `playVideo` once more, then show one line below the player (never over it) telling the visitor to press play. The line SHALL go when the player reports playing or the card leaves the top, and SHALL be announced politely.

#### Scenario: Retry once
- **WHEN** the player reported ready 4 seconds ago and has not reported playing
- **THEN** the page sends `playVideo` a second time, once only

#### Scenario: The line appears below the player
- **WHEN** the player still has not reported playing 3 seconds after the retry
- **THEN** a line telling the visitor to press play in the player is shown below it, nothing is drawn over the player, and the line is a polite live region

#### Scenario: The line goes when playing starts
- **WHEN** the line is shown and the player then reports playing
- **THEN** the line is removed

#### Scenario: A player that never reports ready
- **WHEN** the top card's player has loaded but has reported nothing 7 seconds later
- **THEN** the same line is shown below the player, and it goes if the player later reports playing

#### Scenario: No line when it plays
- **WHEN** the player reports playing before the 4 seconds are up
- **THEN** no retry is sent and no line is shown

### Requirement: A video that cannot be embedded says so
When the top card's YouTube player reports an error that means the video cannot be played in an embed (not found, removed, or embedding not allowed), the card SHALL replace the player with a short message and a link to the video (or channel) on YouTube, opening in a new tab. The card SHALL otherwise keep working: the act's name, its shows, and the swipe, Skip and Add controls.

#### Scenario: Embedding not allowed
- **WHEN** the top card's player reports error 101 or 150
- **THEN** the player is replaced by a message and a link to the video on YouTube, and Skip and Add still work

#### Scenario: Not found or removed
- **WHEN** the top card's player reports error 100
- **THEN** the player is replaced by the same message and link

#### Scenario: A channel match
- **WHEN** a channel-only match's player reports such an error
- **THEN** the message links to the channel on YouTube

### Requirement: A new card's player is created inside the visitor's own action
The player of a card that comes to the top because of a swipe, the Skip button or an arrow key SHALL be created in the same step as that action, after the passed card's player has been removed, so the browser counts the action as the one that started the sound and only one player exists. Save and "Start again" already act in the visitor's action and SHALL keep doing so.

#### Scenario: The next player exists before the animation ends
- **WHEN** a visitor presses Skip and the passed card's slide-off animation is still running
- **THEN** the next card's YouTube player already exists, carrying `autoplay=1`, and the passed card's player is already gone

#### Scenario: Only the new top card is listened to
- **WHEN** a card is skipped and the slide-off animation is still running
- **THEN** a "ready" message from the new top card's frame gets `playVideo`, and one from the passed card's old frame gets nothing

#### Scenario: A double press or held key moves once
- **WHEN** a visitor presses Skip twice quickly, or holds the arrow key down, during the slide-off
- **THEN** the deck moves on by one card only, and only one player is created

#### Scenario: Reduced motion
- **WHEN** the visitor has asked for reduced motion and swipes a card away
- **THEN** the next card's player is created in that same step, in the same order, and swipes, presses and key repeats are ignored until the slide-off ends
