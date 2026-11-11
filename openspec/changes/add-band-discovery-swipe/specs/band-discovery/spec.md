# band-discovery Specification

## Purpose

Lets a visitor flip through the site's bands and artists one card at a time, hear a taste of each, and save the shows of the ones they like to their saved shows, without an account.

## ADDED Requirements

### Requirement: A discovery page holds one card per act with upcoming shows
`/discover` SHALL show a deck with one card for each live band or artist that has at least one upcoming approved show. An act held for review, and an act with no upcoming approved show, SHALL NOT be in the deck. Past, deleted, unapproved and cancelled shows SHALL NOT count or appear on a card or picker. The deck SHALL include acts from every area and SHALL NOT change the remembered filter. With no act, the page SHALL say so and link to the listings.

#### Scenario: An act with an upcoming show
- **WHEN** Belly has an approved show next week
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
- **WHEN** no act has an upcoming approved show
- **THEN** the page says there are no bands to discover yet, and links to the listings

#### Scenario: Area filter ignored
- **WHEN** a visitor's remembered filter is Vermont and Belly's only show is in Rhode Island
- **THEN** Belly is in the deck, and the remembered filter is still Vermont

### Requirement: A card shows the act and a taste of its music
A card SHALL show the act's name, whether it is a band or an artist, its home town and state when known, its photo when it has one (credited as on the act's own page), and its next upcoming show: date, time, venue and town (the show's own venue and time overrides apply, and a show with no venue still shows). The card SHALL link to the act's own page.

#### Scenario: Card contents
- **WHEN** Belly of Providence, RI has a photo and a show on Nov 14 at Lupo's
- **THEN** its card shows the name, "band", "Providence, RI", the photo with its credit, and "Nov 14", the time and "Lupo's", and links to `/bands/belly`

### Requirement: A card plays a taste of the act
A card SHALL show the act's play buttons, as the listings show them, for each of Apple Music and YouTube where the act is matched, and none where it isn't. The card SHALL NOT show a Spotify button or load a Spotify player, even for an act matched on Spotify. Each button SHALL show its service's icon beside its name.

#### Scenario: Play buttons with icons
- **WHEN** Belly is matched on Apple Music and not on YouTube
- **THEN** its card has an Apple Music button with the Apple Music icon, and no other

#### Scenario: Spotify is not used
- **WHEN** Belly is matched on Spotify and Apple Music
- **THEN** its card has an Apple Music button and no Spotify button, and nothing is requested from Spotify

### Requirement: The top card plays the act's music in place of its photo
The card on top SHALL show the act's YouTube video player if it is matched, else its Apple Music player, in place of the photo, ready for the visitor to press its own play control; the page SHALL NOT start the sound by itself. An act with no match SHALL show its photo when it has one. Only the card on top SHALL load a player, and passing or adding the card SHALL stop and remove it. Nothing SHALL load from those services for cards that are not on top.

#### Scenario: Video first
- **WHEN** Belly is matched on YouTube and Apple Music and its card comes to the top
- **THEN** the YouTube player is loaded in the card, not yet playing, and the Apple Music button stays available

#### Scenario: Apple Music when there is no video
- **WHEN** an act is matched on Apple Music only and its card comes to the top
- **THEN** the Apple Music player is loaded in the card, not yet playing

#### Scenario: Spotify only
- **WHEN** an act is matched on Spotify only and its card comes to the top
- **THEN** its card has no play button and no player, and shows its photo if it has one

#### Scenario: No match
- **WHEN** an act has no streaming match
- **THEN** its card has no play button and shows its photo if it has one, and is otherwise complete

#### Scenario: Only the top card loads
- **WHEN** the page loads and later a card is passed
- **THEN** only the top card's player has been requested, and the passed card's player is gone

### Requirement: The player stays unobstructed and swipes start outside it
The in-card player SHALL be at least 200 × 200 px at phone widths, whatever the service, and nothing SHALL be drawn over it: the "Skip" and "Add" hint labels, buttons, the sway and any card text sit outside the player's box. A swipe SHALL start only on the card outside the player, and a touch or pointer that starts inside the player SHALL use the player and never move the card.

#### Scenario: Player size and nothing over it
- **WHEN** a card with a YouTube video is on top at a 390 px wide phone
- **THEN** the player is at least 200 × 200 px and no hint label, button or other element overlaps its box

#### Scenario: Touching the player does not swipe
- **WHEN** a visitor drags starting inside the player
- **THEN** the card does not move and the act is neither passed nor added

#### Scenario: Swiping from outside the player
- **WHEN** a visitor drags the card from outside the player past the threshold
- **THEN** the card is passed or added as for any swipe

### Requirement: A new visitor is taught to swipe
While the first card is shown and the visitor has not yet swiped or pressed a button, the card SHALL sway left and right with the labels "Skip" on the left and "Add" on the right. The hint SHALL stop after the first swipe or button press and SHALL NOT be stored. With reduced motion requested, the labels SHALL show without movement.

#### Scenario: Hint on the first card
- **WHEN** a visitor opens the page
- **THEN** the card sways and the "Skip" and "Add" labels show, until the visitor first swipes or presses a button

#### Scenario: Reduced motion
- **WHEN** the visitor's device asks for reduced motion
- **THEN** the labels show and the card does not move

### Requirement: Swiping left passes an act
Swiping a card left, the skip button, and the left arrow key SHALL each remove the card and show the next one, saving nothing. A pass SHALL NOT be stored, so the act can appear again on a later visit. When the last card is passed, the page SHALL say the deck is finished, and offer to start again and to open the saved shows.

#### Scenario: Pass
- **WHEN** a visitor swipes Belly's card left
- **THEN** the next act's card is shown, and the saved shows are unchanged

#### Scenario: Pass by button or key
- **WHEN** a visitor presses the skip button or the left arrow key
- **THEN** the card passes exactly as a left swipe does

#### Scenario: End of deck
- **WHEN** a visitor skips or adds the last card
- **THEN** the page says the deck is finished, with controls to start again and to open the saved shows

### Requirement: Swiping right lets the visitor choose which shows to save
Swiping a card right, the add button, and the right arrow key SHALL each open a picker listing all of that act's upcoming approved shows, soonest first, each with date, time, venue, town and a checkbox, ticked only if already saved. The picker SHALL open only after such an action, never with a card on its own.

#### Scenario: Picker lists the act's shows
- **WHEN** Belly has shows on Nov 14, Nov 20 and Dec 2 and a visitor swipes its card right
- **THEN** a picker lists the three, soonest first, each with date, time, venue and town, none ticked because none is saved

#### Scenario: Picker only after adding
- **WHEN** a card is shown and the visitor has not swiped right or pressed add
- **THEN** no picker is open

### Requirement: Tapping a show's row ticks it and Save applies the ticks
Tapping anywhere in a show's row SHALL tick or untick it, not only the checkbox. The picker SHALL have a Save button that says how many shows are ticked, and ticking alone SHALL save nothing. Pressing Save SHALL add each newly ticked show and remove each unticked saved show, then show the next card. Pressing Save with the ticks unchanged from what was saved SHALL change nothing and keep the picker open.

#### Scenario: Tapping the row ticks it
- **WHEN** the visitor taps the text of a show's row, away from its checkbox
- **THEN** the show is ticked, and tapping again unticks it

#### Scenario: Save more than one
- **WHEN** the visitor ticks the Nov 14 and Dec 2 shows and presses "Save 2 shows"
- **THEN** both shows' IDs are in the `saved_shows` cookie, the header reads "Saved shows (2)" (with JavaScript on, as on the listings) and the next card is shown

#### Scenario: Nothing ticked
- **WHEN** Belly has no saved show and the visitor confirms with no show ticked
- **THEN** nothing is saved and the picker stays open

#### Scenario: Removing the last saved show
- **WHEN** Belly's Nov 20 show is its only saved show, and the visitor unticks it and confirms
- **THEN** the Nov 20 show is removed from the `saved_shows` cookie and the next card is shown

#### Scenario: Nothing changed
- **WHEN** Belly's Nov 20 show is saved, and the visitor confirms with it still the only one ticked
- **THEN** nothing changes and the picker stays open

#### Scenario: Other saved shows kept
- **WHEN** a visitor has saved a show by Anjimile, then ticks a Belly show in the picker and confirms
- **THEN** the cookie holds both the Belly show and the Anjimile show

#### Scenario: Adding on the last card
- **WHEN** the visitor ticks a show on the last card and presses Save
- **THEN** the show is saved and the page says the deck is finished

#### Scenario: Saved shows page
- **WHEN** a visitor saves a show from the picker and opens `/saved`
- **THEN** the show is listed there like any other saved show

#### Scenario: Limit
- **WHEN** a visitor already has 300 saved shows and saves another from the picker
- **THEN** the new one is kept and the oldest saved is dropped, as on the listings

### Requirement: The picker closes without changing anything and shows what is already saved
Closing the picker SHALL change nothing and return to the same card. A show already saved SHALL be ticked and marked "Saved" when the picker opens, and unticking it SHALL remove it when confirmed.

#### Scenario: Ticking alone saves nothing
- **WHEN** the visitor ticks a show and does not press Save
- **THEN** the `saved_shows` cookie is unchanged

#### Scenario: Cancel
- **WHEN** the visitor ticks a show and closes the picker
- **THEN** nothing is saved and Belly's card is shown again

#### Scenario: Already saved
- **WHEN** the visitor saved Belly's Nov 20 show earlier and swipes its card right
- **THEN** the Nov 20 show is ticked and marked "Saved", and unticking it and confirming removes it from the cookie

### Requirement: The deck works without a swipe and without JavaScript
The skip and add buttons and the arrow keys SHALL give every swipe action without a touch screen, and SHALL be reachable and named for assistive technology. The deck SHALL announce the current act when the card changes. With JavaScript off, the page SHALL list every card in the deck one after another, each with its upcoming shows and the save bookmark the listings use, which saves through the server as it does on the listings.

#### Scenario: Keyboard only
- **WHEN** a visitor uses only the keyboard, on a page with JavaScript
- **THEN** they can skip, add, tick shows, confirm and close the picker

#### Scenario: Card change announced
- **WHEN** the next card is shown
- **THEN** its act's name is announced to a screen reader

#### Scenario: No JavaScript
- **WHEN** JavaScript is off and a visitor opens `/discover`
- **THEN** every card is listed with its shows, and clicking a show's bookmark posts to `/saved/toggle/<id>` and returns the visitor to that show on the page

#### Scenario: A show on two cards
- **WHEN** a show is on two cards (an act that is both an artist and a band, or a member's show) and JavaScript is off
- **THEN** each card's copy of the show has its own anchor, and saving it from a card returns the visitor to that card

### Requirement: The page has the site's own header and menu
`/discover` SHALL show the same masthead as the home page and every other page: the title linking home, the saved shows count, the header menu items, the burger menu, the search box and the footer menu, with the links in the same places. The page SHALL NOT have a header of its own.

#### Scenario: Same header as the home page
- **WHEN** a visitor opens `/discover`
- **THEN** the masthead, search box and menu links are the ones `/` shows, in the same order

### Requirement: The page is linked from the menu
The site's menu SHALL link to `/discover` as "Discover bands", in the header and the footer, as a menu item a data migration adds once, so editors can move or hide it in the admin.

#### Scenario: Menu link
- **WHEN** a visitor opens any page's menu
- **THEN** it has a "Discover bands" link to `/discover`

#### Scenario: Migration adds the item once
- **WHEN** the migration runs twice
- **THEN** there is one "Discover bands" menu item
