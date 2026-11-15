## MODIFIED Requirements

### Requirement: A discovery page holds one card per act with upcoming shows
`/discover` SHALL show a deck with one card for each live band or artist that has at least one upcoming approved show and something to play (see "The deck holds only acts with something to play"). An act held for review, and an act with no upcoming approved show, SHALL NOT be in the deck. Past, deleted, unapproved and cancelled shows SHALL NOT count or appear on a card or picker. With no filter chosen the deck SHALL include acts from every area. With no act, the page SHALL say so and link to the listings.

#### Scenario: An act with an upcoming show
- **WHEN** Belly has an approved show next week and is matched on Apple Music
- **THEN** the deck holds one card for Belly

#### Scenario: Acts left out
- **WHEN** Anjimile has only a past show, and "3 1/2 Girls" is held for review but has an upcoming show
- **THEN** neither is in the deck

#### Scenario: Cancelled shows
- **WHEN** Belly has one cancelled and one live upcoming show, and Anjimile has only a cancelled upcoming show
- **THEN** Belly's card and picker have the live show only, and Anjimile is not in the deck

#### Scenario: One card for several shows
- **WHEN** Belly has three upcoming shows
- **THEN** the deck holds one card for Belly, not three

#### Scenario: Empty deck
- **WHEN** no act has an upcoming approved show and something to play
- **THEN** the page says there are no bands to discover yet, and links to the listings

#### Scenario: Area filter ignored
- **WHEN** a visitor's remembered filter is Vermont and Belly's only show is in Rhode Island
- **THEN** Belly is not in the deck, because the deck now follows the remembered filter, and the remembered filter is still Vermont

#### Scenario: No filter chosen
- **WHEN** a visitor with no remembered filter opens `/discover`, and Belly's only show is in Rhode Island
- **THEN** Belly is in the deck

### Requirement: A card shows the act
A card SHALL show the act's name, whether it is a band or an artist, its home town and state when known, and its next upcoming show in the chosen areas: date, time, venue and town (the show's own venue and time overrides apply, and a show with no venue still shows). The card SHALL link to the act's own page. A card SHALL NOT show a photo, because every card has a player.

#### Scenario: Card contents
- **WHEN** Belly of Providence, RI is matched on YouTube and has a show on Nov 14 at Lupo's
- **THEN** its card shows the name, "band", "Providence, RI", and "Nov 14", the time and "Lupo's", links to `/bands/belly`, and shows no photo

### Requirement: The top card plays the act's music in place of its photo
The card on top SHALL show the act's YouTube video player if it is matched, else its Apple Music player, else its Spotify player. Only the card on top SHALL load a player, and passing or adding the card SHALL stop and remove it. Nothing SHALL load from those services for cards that are not on top. Whether and how the player starts by itself is set by "The top card starts playing after a visitor's action".

#### Scenario: Video first
- **WHEN** Belly is matched on YouTube and Apple Music and its card comes to the top
- **THEN** the YouTube player is loaded in the card, and the Apple Music button stays available

#### Scenario: Apple Music when there is no video
- **WHEN** an act is matched on Apple Music only and its card comes to the top
- **THEN** the Apple Music player is loaded in the card

#### Scenario: Spotify last
- **WHEN** an act is matched on Spotify and Apple Music and its card comes to the top
- **THEN** the Apple Music player is loaded, and the Spotify button stays available but no Spotify player is requested

#### Scenario: Spotify only
- **WHEN** an act is matched on Spotify only and its card comes to the top
- **THEN** the Spotify player is loaded in the card

#### Scenario: No match
- **WHEN** an act has no streaming match
- **THEN** it is not in the deck, so no card has no player

#### Scenario: Only the top card loads
- **WHEN** the page loads and later a card is passed
- **THEN** only the top card's player has been requested, and the passed card's player is gone

### Requirement: A new visitor is taught to swipe
Once the visitor has pressed Start and the first card is shown, and until the visitor has swiped or pressed a button, the card SHALL sway left and right with the labels "Skip" on the left and "Add" on the right. Before Start, the hint SHALL NOT run. The hint SHALL stop after the first swipe or button press and SHALL NOT be stored. With reduced motion requested, the labels SHALL show without movement.

#### Scenario: Hint on the first card
- **WHEN** a visitor opens the page and presses Start
- **THEN** the card sways and the "Skip" and "Add" labels show, until the visitor first swipes or presses a button

#### Scenario: Reduced motion
- **WHEN** the visitor's device asks for reduced motion
- **THEN** the labels show and the card does not move

### Requirement: Swiping left passes an act
Swiping a card left, the skip button, and the left arrow key SHALL each remove the card and show the next one, saving nothing. A pass SHALL NOT be stored, so the act can appear again on a later visit. When the last card is passed, the page SHALL say the deck is finished, and offer to start again and to open the saved shows. Pressing "start again" counts as the visitor's action: it SHALL show the first card with its player asking to start, without the Start control.

#### Scenario: Pass
- **WHEN** a visitor swipes Belly's card left
- **THEN** the next act's card is shown, and the saved shows are unchanged

#### Scenario: Pass by button or key
- **WHEN** a visitor presses the skip button or the left arrow key
- **THEN** the card passes exactly as a left swipe does

#### Scenario: End of deck
- **WHEN** a visitor skips or adds the last card
- **THEN** the page says the deck is finished, with controls to start again and to open the saved shows

#### Scenario: Start again
- **WHEN** a visitor presses "start again" at the end of the deck
- **THEN** the first card is shown with its player asking to start playing, and the Start control does not come back

### Requirement: Swiping right lets the visitor choose which shows to save
Swiping a card right, the add button, and the right arrow key SHALL each open a picker listing all of that act's upcoming approved shows in the chosen areas (all of them when no filter is set), soonest first, each with date, time, venue, town and a checkbox, ticked only if already saved. The picker SHALL open only after such an action, never with a card on its own.

#### Scenario: Picker lists the act's shows
- **WHEN** Belly has shows on Nov 14, Nov 20 and Dec 2 and a visitor swipes its card right
- **THEN** a picker lists the three, soonest first, each with date, time, venue and town, none ticked because none is saved

#### Scenario: Picker only after adding
- **WHEN** a card is shown and the visitor has not swiped right or pressed add
- **THEN** no picker is open

#### Scenario: Picker under a filter
- **WHEN** Belly has shows in Burlington, VT on Nov 14 and in Providence, RI on Nov 20, and a visitor opens `/discover?state=vermont` and swipes its card right
- **THEN** the picker lists the Nov 14 show only

## ADDED Requirements

### Requirement: The deck holds only acts with something to play
An act SHALL be in the deck only when at least one of its YouTube, Apple Music or Spotify play buttons would show on its card, by the same links, switches and credentials as the listings. An act with no match, or whose matches are all switched off, SHALL NOT be in the deck, whatever shows or photo it has, in the swiped deck and in the no-JavaScript list alike. Its own page and the listings SHALL NOT change.

#### Scenario: An act with no media
- **WHEN** Anjimile has an upcoming show, no YouTube, Apple Music or Spotify match and a photo
- **THEN** Anjimile is not in the deck

#### Scenario: An act with one service
- **WHEN** Belly has an upcoming show and only a Spotify match
- **THEN** Belly is in the deck

#### Scenario: A match that cannot play
- **WHEN** an act's only match is Apple Music with no top song, or its service's switch is off
- **THEN** the act is not in the deck

#### Scenario: No JavaScript
- **WHEN** JavaScript is off and Anjimile has no media
- **THEN** the list does not include Anjimile

### Requirement: The deck can be filtered by region, state and metro area
`/discover` SHALL offer the Region, State and Metro Area filters the listing offers (with the metro's towns and neighborhoods), as a plain GET form chosen with the `region`, `state`, `metro`, `town` and `neighborhood` query parameters, working without JavaScript, with the same areas, membership rules and handling of unknown values as the listing.

#### Scenario: Unknown value
- **WHEN** a visitor opens `/discover?state=atlantis`
- **THEN** the page returns 200 and the deck is unfiltered

#### Scenario: Metro options follow the state
- **WHEN** a visitor has chosen Massachusetts
- **THEN** the Metro Area options are the Massachusetts metros only, as on the listing

### Requirement: A filter narrows the deck's acts and shows
When a filter is set, the deck SHALL hold only acts with an upcoming approved show at a venue in the chosen areas, and each card and picker SHALL list only those shows. Filters given together SHALL all apply. A show with no linked venue SHALL match no filter.

#### Scenario: Filter by state
- **WHEN** a visitor opens `/discover?state=vermont`, and Belly has a show in Vermont while Anjimile's only show is in Rhode Island
- **THEN** the deck holds Belly and not Anjimile, and the State filter shows Vermont as selected

#### Scenario: Only the shows in the area
- **WHEN** Belly has shows in Burlington, VT and Providence, RI and a visitor opens `/discover?state=vermont`
- **THEN** Belly's card and picker list the Burlington show only

#### Scenario: Region and metro
- **WHEN** a visitor opens `/discover?region=new-england&metro=ma-boston`
- **THEN** the deck holds only acts with an upcoming show at a venue in that metro

#### Scenario: Nothing matches the filters
- **WHEN** a filter leaves no act with something to play
- **THEN** the page says no bands match the filters and links to the unfiltered deck

### Requirement: The deck uses the listing's remembered filter
The deck SHALL use the same remembered-filter cookie as the listing, with the same rules: opening `/discover` with a valid filter saves it; opening it with no filter parameter while the cookie holds a valid filter redirects to `/discover` with that filter's parameters; "All" or the show-all link clears it; a stale cookie is deleted without a redirect. A filter chosen on the deck SHALL therefore apply to the listing and the other way round.

#### Scenario: Filter chosen on the deck is remembered
- **WHEN** a visitor opens `/discover?state=vermont` and later opens `/`
- **THEN** the second request redirects to `/?state=vermont`

#### Scenario: Listing filter applies to the deck
- **WHEN** a visitor whose cookie holds `state=vermont` opens `/discover`
- **THEN** the request redirects to `/discover?state=vermont`

#### Scenario: Clearing
- **WHEN** a visitor with a remembered filter follows the show-all link on the deck
- **THEN** the unfiltered deck is shown and the cookie is deleted

#### Scenario: A shared link wins
- **WHEN** a visitor whose cookie holds `state=vermont` opens `/discover?state=maine`
- **THEN** Maine acts are in the deck and the cookie holds `state=maine`

### Requirement: The top card starts playing after a visitor's action
Browsers allow sound to start by itself only after the visitor has acted on the page, so the first card SHALL wait for one: until the visitor has pressed a start control, the deck SHALL load no player. The start control SHALL be laid over a placeholder, which SHALL be removed with it when the player loads. The placeholder is the first card's video thumbnail (top card only) or, when there is none or the design's open question 10 does not allow it, a plain dark box.

#### Scenario: Nothing plays before the visitor acts
- **WHEN** a visitor opens `/discover`
- **THEN** a start control is shown and no YouTube, Apple Music or Spotify player is requested

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
- **WHEN** the first card is matched on Apple Music or Spotify only and the visitor presses Start
- **THEN** its player is loaded ready, with its own play control, and the hint and controls appear

### Requirement: Each later card starts by itself
After the start control, each card that comes to the top because of a swipe, a button or an arrow key SHALL load its player asking the service to start playing. For YouTube, the player SHALL be loaded with `autoplay=1` and an `allow` that includes autoplay. For other services, see "Apple Music and Spotify cards load ready". Nothing SHALL be drawn over the player, and the sound of a passed or added card SHALL stop when its player is removed.

#### Scenario: Next card starts by itself
- **WHEN** the visitor skips a card and the next is matched on YouTube
- **THEN** the next card's YouTube player is loaded asking to start playing, and the passed card's player is gone

#### Scenario: A service that cannot be started
- **WHEN** the next card is matched on Apple Music or Spotify only
- **THEN** its player is loaded ready, not started, with its own play control

#### Scenario: After saving
- **WHEN** the visitor saves shows in the picker
- **THEN** the next card's player starts as after a skip

#### Scenario: Keyboard
- **WHEN** the visitor starts the deck and moves through it with the arrow keys
- **THEN** each new top card's player is loaded asking to start playing

### Requirement: Apple Music and Spotify cards load ready
Apple Music and Spotify cards SHALL load ready, with their own play control. Spotify's iFrame API script SHALL NOT be loaded. A later change may amend this if a documented way to start them is approved.

#### Scenario: Ready, not started
- **WHEN** a card matched on Apple Music or Spotify only comes to the top
- **THEN** its player is loaded without being started and no Spotify iFrame API script is requested

### Requirement: Right adds to the saved shows and left skips
On a touch screen and with a mouse, a swipe right SHALL open the picker to add the act's shows to the visitor's saved shows, and a swipe left SHALL skip the act, saving nothing. The labels SHALL sit on the side they act on, "Skip" on the left and the add label on the right. This restates the existing mouse, button and key behaviour and adds the touch screen; it changes none of it.

#### Scenario: Touch swipe right
- **WHEN** a visitor drags a card to the right with a finger on a phone-sized screen
- **THEN** the picker opens and nothing has been skipped

#### Scenario: Touch swipe left
- **WHEN** a visitor drags a card to the left with a finger on a phone-sized screen
- **THEN** the next card is shown, nothing is saved and no picker opens

### Requirement: The deck is ordered by each act's soonest show
The deck SHALL put the acts in order of their next upcoming show in the chosen areas, soonest first, so the cards a visitor sees first are the imminent ones and shows months away come last. Acts whose next show falls on the same calendar day (New York time) SHALL be in a random order among themselves for each visit. A show's date, not the act's name or a random draw across the whole deck, SHALL decide where its card falls.

#### Scenario: Imminent acts come first
- **WHEN** Belly plays tomorrow, Anjimile plays in three weeks and Frankie Cosmos plays in April 2027, all with something to play
- **THEN** the deck is in the order Belly, Anjimile, Frankie Cosmos

#### Scenario: Next show decides, not the last
- **WHEN** Anjimile has shows tomorrow and in April 2027, and Belly has one show in three weeks
- **THEN** Anjimile's card comes before Belly's

#### Scenario: Order follows the filter
- **WHEN** a visitor filters to Vermont, Belly plays in Rhode Island tomorrow and in Vermont in April 2027, and Anjimile plays in Vermont next month
- **THEN** Anjimile's card comes before Belly's, because only Vermont shows count

#### Scenario: Same day in a random order
- **WHEN** Belly and Anjimile both play tomorrow, on different visits
- **THEN** both come before any act playing later, and their order between them may differ from visit to visit

