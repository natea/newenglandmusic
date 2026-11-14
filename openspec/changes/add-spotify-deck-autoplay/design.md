# Design

## Context

- The deck (`core/static/core/js/discover.js`) puts the top card's player in place with `ArtistPreview.showInCard(card, button, autoplay)` (`core/static/core/js/artist_preview.js`). With `autoplay`, YouTube's embed gets `autoplay=1&playsinline=1`; Spotify's and Apple Music's iframes load ready. The first card waits for a Start control, so every start follows a visitor's action.
- Spotify's iFrame API (developer.spotify.com/documentation/embeds/references/iframe-api): a script defines `window.onSpotifyIframeApiReady(IFrameAPI)`; `IFrameAPI.createController(element, {uri, width, height}, callback)` replaces the element with the embed and gives a controller with `play()`, `pause()`, `destroy()` and `ready`, `playback_started` and `playback_update` events. Its docs warn that `play` without the visitor's own interaction "might not be supported in all browsers and for all users", and that Safari blocks it. They show track and episode URIs; artist URIs aren't documented.
- Apple Music's embed takes no start parameter and has no scripting API.

## Goals / Non-Goals

**Goals:** a Spotify-only card plays by itself where the browser allows; where it doesn't, the card is exactly as today.

**Non-Goals:** Apple Music autoplay (no documented way; previews in our own player need a terms review); autoplay in the listings; changing which service a card plays when it has several.

## Decisions

### 1. The controller only in the deck, only after Start
`spotifyPlayer(button, height, autoplay)`: without `autoplay` it's today's plain iframe. With it, the deck loads `https://open.spotify.com/embed/iframe-api/v1` once (a `<script async>`, on the first Spotify card after Start), waits for `onSpotifyIframeApiReady`, and calls `createController(slot, {uri: "spotify:artist:<id>", width: "100%", height}, …)`; on the controller's `ready` it calls `play()`.

### 2. Fall back to ready, quietly
If the script fails to load or `onSpotifyIframeApiReady` doesn't come within 5 seconds, the card gets today's plain iframe. If `play()` starts nothing (no `playback_started` within 4 seconds), nothing more is done: the embed is loaded, with its own play control. If artist URIs turn out unsupported by the controller, the first trial (task 1.1) decides between the artist's top track's URI (which would mean storing a track ID: a spec change, so it'd come back here) and dropping Spotify autoplay.

### 3. Sound stops when a card leaves
The deck keeps the card's controller and calls `destroy()` when the card is passed or added, as removing YouTube's iframe stops its sound.

### 4. One script, from Spotify, after the visitor acts
The script runs in our page, unlike the players, which run in Spotify's iframe. It loads only in the deck after Start, never in the listings, and the privacy page says so.

## Risks / Trade-offs

- **Safari and iPhones will likely refuse to start it,** since the tap was on our page, not inside Spotify's frame. Those visitors get today's behaviour. The trial records which browsers start it.
- **Logged-out visitors hear 30-second previews,** as they do now when they press play.
- **Spotify can change its script;** the fallback keeps cards working if it breaks.

## Testing

- Django and Playwright tests never touch the network: the browser tests route `open.spotify.com/embed/iframe-api/v1` to a stub script that defines a fake `IFrameAPI`, recording `createController`'s URI and `play()` calls and firing `ready`/`playback_started` on cue, and route the embed iframe to a blank page.
- Covered: no Spotify script before Start; a Spotify card after Start creates a controller for the artist and calls `play()`; a script that never loads falls back to the plain iframe; passing the card destroys the controller; the listing's Spotify button still loads the plain iframe and no script; an Apple Music card loads ready.
