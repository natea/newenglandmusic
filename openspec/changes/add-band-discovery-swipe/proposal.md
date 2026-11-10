Issue: [#26 build a tinder-style band discovery tool on the site](https://github.com/natea/newenglandmusic/issues/26)

## Why

Issue 26 asks for a Tinder-style band discovery tool modeled on the New Orleans Jazz Fest discovery site. The site already knows its acts, which of them have upcoming shows, and how to play a taste of each; what it lacks is a way to browse acts one at a time and turn interest in a band into a plan to see it. A fan who doesn't know the lineup can flip through bands, hear a taste, and keep the shows they want.

## What Changes

- **A discovery page** at `/discover`: a deck of cards, one card per band or artist, swiped or tapped through one at a time. A card shows the act's name, kind, home town, photo when it has one, its next show, and the play buttons the listings already have.
- **Who is in the deck:** live acts (not held for review) with at least one upcoming approved show that is not cancelled. Acts with none are left out, and cancelled shows are left out of the card and the picker.
- **Swipe left** (or the pass button, or the left arrow key) skips the act and shows the next card.
- **Swipe right** (or the keep button, or the right arrow key) opens a picker of that act's upcoming shows, with date, time, venue and town. Shows already saved are ticked when it opens. The visitor ticks one or more and confirms; the picker's ticks become that act's saved shows (newly ticked shows are added, unticked saved shows are removed). Closing the picker without confirming changes nothing and returns to the card.
- **Reuses saved shows:** the same `saved_shows` cookie, the same 300-show limit, the same header count and the same `/saved` page. Nothing new is stored about the visitor, and no account is needed.
- **Without JavaScript** the deck is a plain list of the same cards, each listing its shows with the existing save bookmark, so the page still works.
- **A menu link** to the page, as a menu item added by a data migration (in the header and footer, editable in the admin), like the "Bands & artists" link.

## Capabilities

### New Capabilities
- `band-discovery`: the swipe deck, which acts it holds, what a card shows, and how a right swipe saves shows.

### Modified Capabilities
<!-- none: saved-shows' behavior is reused unchanged -->

## Impact

- **Code:** a new view and template for `/discover`, a script for swiping and the picker, styles, a URL, and a data migration adding the menu item. A small change to `saved_shows.js` to expose its cookie code to the new script, which also loads on every page. A function that builds an act's play buttons from its name, reusing the stored Spotify, Apple Music and YouTube links the listings use.
- **No model or schema change (the one migration only adds a menu row), no new cookie, no new external API or paid call.** Previews read links already stored; nothing is fetched from Spotify, Apple Music or YouTube when the page loads.
- **Screens:** the deck, the card, and the show picker are new screens, so this change needs a design round (`needs-design`).
- **Open questions** (see `design.md`): what the reference site does that should be copied, whether the deck follows the visitor's area filter, and whether passes are remembered.
