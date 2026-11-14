## Why

In the band discovery deck, a YouTube card starts playing as soon as it comes to the top, but a Spotify-only card waits for the visitor to press play in Spotify's player, which breaks the swipe-and-listen flow. The deck change that added autoplay left this as an open question ("may the deck load Spotify's iFrame API script?"); this change answers it. Spotify documents a way to start its player from the page; Apple Music doesn't.

## What Changes

- **In the discovery deck, a Spotify-only card is asked to start playing** when it comes to the top after the visitor's action (Start, a swipe, a button or an arrow key), as YouTube cards are. The deck loads Spotify's iFrame API script, builds the card's player with its controller, and calls `play()`.
- **If a browser won't start it** (Safari and phones may block sound that the visitor didn't start inside Spotify's own player), the player stays loaded and ready with its own play control, as today. Nothing is drawn over it.
- **Nothing changes before the visitor acts, or in the listings:** no Spotify script loads before Start, and the listing's Spotify buttons stay click-to-play with the plain embed.
- **Apple Music cards stay ready, not started:** Apple's embedded player has no documented way to start it. Playing its 30-second preview in our own audio player instead would need Apple's terms for previews checked first, so it's left for a later change.
- **The privacy page** says the deck loads Spotify's player script after Start.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `band-discovery`: Spotify cards are asked to start like YouTube cards; only Apple Music cards load ready.

## Impact

- **Code:** `core/static/core/js/artist_preview.js` (a Spotify player built with the iFrame API's controller when the deck asks to start), `core/static/core/js/discover.js` (destroying the controller when a card leaves), `core/templates/core/privacy.html`.
- **Outside services:** Spotify's iFrame API script (`https://open.spotify.com/embed/iframe-api/v1`), loaded only in the deck after Start. Free; no key.
- **Depends on** `improve-band-discovery` (built, not yet archived; its tasks 3.4 and 5.1 are open), which adds the `band-discovery` requirements this modifies; archive it first.
