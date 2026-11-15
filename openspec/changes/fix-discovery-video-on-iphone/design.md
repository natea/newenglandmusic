Issue: [#104 YouTube videos don't play on mobile](https://github.com/natea/newenglandmusic/issues/104)

Issue: [#104 YouTube videos don't play on mobile](https://github.com/natea/newenglandmusic/issues/104)

## Context

- The thread settled: the problem is only on the band discovery deck, on iOS Chrome and Safari. After Start the card shows YouTube's thumbnail and play button; tapping play works. The listings stay as they are (no autoplay there).
- `core/static/core/js/discover.js` loads the player inside the Start click handler (`startDeck` → `loadPlayer` → `ArtistPreview.showInCard(card, button, true)`), and `core/static/core/js/artist_preview.js` `youtubePlayer` builds an iframe whose address ends `autoplay=1&playsinline=1`, with `allow="autoplay; ..."`. So the existing code already follows the documented route, which works on desktop Chrome. iOS evidently treats an iframe's `autoplay` parameter as not allowed, even after a tap, because the iframe loads after the tap's event turn ends.
- Every iOS browser uses Safari's engine, which explains why Chrome and Safari on the phone behave alike.
- The deck's spec is in the unarchived changes `add-band-discovery-swipe` and `improve-band-discovery` ("Each later card starts by itself", "Start begins the first card"); this change adds a capability beside it.
- No YouTube script is loaded anywhere today. The owner decided on 2026-10-28 against YouTube's IFrame API ("Why no IFrame API: we don't need it. A plain iframe loads no YouTube script before a click", in `archive/2026-10-28-add-youtube-artist-preview/design.md`). The note below needs it, so this change would reverse that decision on the iPhone path of the deck only; `improve-band-discovery` likewise says Spotify's script shall not be loaded, though a later change may amend that. This is for the owner to confirm (open question 1).

## Goals / Non-Goals

**Goals:** the video starts after Start on iPhone as on desktop where iOS permits, and where it doesn't, the card says one tap is needed.
**Non-Goals:** the listings' players; Apple Music and Spotify cards; our own volume controls; changes to Start or swipe behaviour on desktop.

## Decisions

### 1. Two candidate ways to start on iOS (not yet chosen)
- **A. Muted autoplay (`mute=1` in the embed address).** iOS generally allows muted inline autoplay. The video would start silently and the visitor would unmute in YouTube's own player. Smallest change (one parameter, desktop could stay unmuted); but a silent start on a music tool is a weak result, and it is not certain iOS permits it from an iframe loaded in this way.
- **B. YouTube's IFrame Player API.** The page loads YouTube's script, builds the player, and calls `playVideo()` from the visitor's tap. iOS still requires the call to follow the tap closely, so the player may need to exist before the tap, which conflicts with "nothing loads from YouTube before Start" (the privacy stance). A variant creates the player in the Start handler and calls `playVideo()` when it reports ready, which iOS may refuse.
The build begins with a real-phone spike (task 1.1) of A and B on the actual deck, and records the result here. The fallback in all cases is decision 2.

### 2. A tap-to-play note as the floor, detected through the IFrame API
The embed is a cross-origin iframe, and its address has no `enablejsapi=1`, so the page cannot tell whether the video started without YouTube's IFrame Player API. So on iOS the deck loads that script after Start, under every route (A included: the iframe gets `enablejsapi=1` and the page listens to state changes), and, if the video is asked to play and doesn't report playing within a short wait, shows a note beside the player (not over it, since YouTube's rules forbid anything over its player) saying to tap play. This turns today's silent thumbnail into an explained state, and makes the outside script, its privacy-page line and its `PRODUCTION.md` line unconditional (task 4.1), not tied to route B. Desktop is unchanged: its address keeps exactly `autoplay=1&playsinline=1`, with no `enablejsapi`, so the existing exact-address assertions in `core/tests/test_discover_browser.py` (around lines 334 and 341) stay true for desktop, and iPhone tests assert the new address. If the owner would rather not load the script, the fallback is a timer-only note, which can't tell a playing video from a stuck one, so it would show on playing videos too; the design does not recommend it (open question 1). The wait length and the wording are open questions below.

### 3. Scope by platform
Behaviour changes only where the spike shows iOS needs it; desktop keeps `autoplay=1` as now. Detecting iOS (including iPadOS reporting as a Mac) is done by feature detection where possible, user-agent only if no feature test exists; open question 3.

## Risks / Trade-offs

- iOS may refuse every route from an iframe; the spec then delivers the note (Requirement 2), and the first requirement only promises that the player is asked to play, so it can pass whatever the spike finds. Task 1.2 makes the route concrete.
- Loading YouTube's script (B) adds an outside script and a privacy line to disclose.
- iOS rules change between versions; the by-hand phone check (task 3.1) can't be automated.

## Testing and mocks

Tests never touch the network. The browser tests in `core/tests/test_discover_browser.py` already route YouTube embed addresses to a stub; this change routes the IFrame API script (which the existing "page requests nothing before Start" test must also check for) to a stub that exposes a fake `YT.Player` whose state the test controls (ready, playing, not playing), and the embed iframe to a blank page. iOS is emulated by Playwright's iPhone device profile (WebKit if installed, else Chromium with the iPhone user agent and touch), which only checks our code paths, not Apple's real rules; the real-phone check is by hand. Thumbnails (`i.ytimg.com`) are routed to a tiny image. No other outside service is involved.

## Open Questions

1. Which route (A muted, B IFrame API, or something the spike finds) is acceptable? A silent start may not be wanted. Both routes now load YouTube's IFrame API script after Start on iPhone, to detect playback, which reverses the 2026-10-28 "Why no IFrame API" decision for that path; the owner confirms that, or chooses the timer-only note, after the spike.
2. If the phone refuses every route, is the "tap play" note enough, or should the deck stop calling YouTube cards "plays on its own" in the Start note's wording ("Music plays on its own once you start") on phones?
3. How should iOS be detected: feature test, or user agent?
4. How long should the wait be before the note shows, and what exact wording?
5. Should this also cover later cards started by a touch swipe, whose pointer events may not count as a tap on iOS? The thread only reported Start; the spike should check it, and the answer may be that swipes need the same note.

## Sketches

Three options for the "tap play" note and the states around it (a phone card in three states, shown at 1440×900):

- [Option A](sketches/a.html): **Plain line under the player.** One quiet line beneath the player says one tap is needed, shown only after the wait, and nothing else on the card changes. *Risk:* easy to miss under a dark player on a small screen, and it says nothing about sound if a muted start is chosen.
- [Option B](sketches/b.html): **Muted start, then an unmute prompt.** The video starts silent, which iPhones allow, and a line below tells the visitor how to turn sound on; the tap-play line is the fallback if the phone still refuses. *Risk:* a silent start on a music tool is a weak result, and it is not certain iOS permits it from this iframe.
- [Option C](sketches/c.html): **Callout above the player that points down.** A louder card-stock callout with a plum edge sits above the player and points at it, and the Start note warns iPhone visitors beforehand. *Risk:* pushes the player down the card, and the louder note may feel like an error rather than a normal step.
