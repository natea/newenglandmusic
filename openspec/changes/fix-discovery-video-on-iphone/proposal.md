Issue: [#104 YouTube videos don't play on mobile](https://github.com/natea/newenglandmusic/issues/104)

Issue: [#104 YouTube videos don't play on mobile](https://github.com/natea/newenglandmusic/issues/104)

## Why

On the band discovery deck (`/discover`), the first card's YouTube video starts by itself after Start on desktop Chrome, but on Chrome and Safari for iOS it shows only YouTube's thumbnail and play button. The video is not broken: it plays when the visitor taps play. The deck's own code already asks for `autoplay=1&playsinline=1` when Start is pressed, and iOS evidently does not count that as permission, so the deck needs another way to start the video, or a clear signal that one tap is needed.

## What Changes

- On iPhone Chrome and Safari, the deck tries to get the YouTube video playing right after Start (and after each later swipe, button or key), by asking the player to play. Which route is an open question in the design (muted start with an unmute prompt, or YouTube's IFrame Player API started from the visitor's tap).
- If the phone still refuses, the card says plainly that one tap on play is needed, instead of showing a silent thumbnail with no explanation.
- Desktop behaviour stays as it is: the video starts by itself after Start.
- Out of scope, as the issue says: the listings' play buttons stay press-to-play with no autoplay. Apple Music and Spotify cards stay as they are (they load ready).

## Capabilities

### New Capabilities
- `discovery-deck-playback`: how the discovery deck starts a card's YouTube video on phones, and what it shows when the phone refuses.

### Modified Capabilities
<!-- none: the deck's spec (`band-discovery`) is still in the unarchived changes `add-band-discovery-swipe` and `improve-band-discovery`, not in `openspec/specs/`, so this change adds a capability beside it; fold it in when those are archived. -->

## Impact

- `core/static/core/js/discover.js` and `core/static/core/js/artist_preview.js` (the YouTube player the deck builds), possibly `discover.html` and `discover.scss` for the "tap play" note.
- On iPhone, a script from YouTube (the IFrame Player API) loads on `/discover` after Start, under every route, so the deck can tell whether the video started. It reverses the owner's 2026-10-28 decision against that script, so the owner confirms it; the privacy page and `PRODUCTION.md` say so. Desktop's embed address and the listings are unchanged.
- Tests: browser tests in `core/tests/test_discover_browser.py` with YouTube's embed and script routed to a stub; no network.
- Depends on `add-band-discovery-swipe` and `improve-band-discovery` being archived first, since it builds on the deck they describe.
