# Tasks

## 1. Try it first

- [ ] 1.1 By hand, in the deck on the local site with real matches, start a Spotify artist through the iFrame API controller (`spotify:artist:<id>`) in Chrome and Safari on a desktop and on an iPhone, signed in and out of Spotify; record in the design which start, and whether the controller takes an artist URI. If it doesn't, stop and revise the design (Decision 2).

## 2. The player

- [ ] 2.1 Build the deck's Spotify player with the iFrame API controller when asked to start: load the script once after Start, create the controller, `play()` on ready, fall back to the plain embed if the script doesn't arrive within 5 seconds; leave the listing's player as it is.
- [ ] 2.2 Destroy a Spotify card's controller when the card is passed or added.
- [ ] 2.3 Verify with Playwright tests, routing the script to a stub `IFrameAPI` and the embed to a blank page: "Nothing plays before the visitor acts", "Start gates any service", "A Spotify card is asked to start", "The script once", "The script can't be loaded", "Sound stops when the card leaves", "The listing stays click-to-play", "Ready, not started" and "A service that cannot be started".

## 3. Finish

- [ ] 3.1 Say on the privacy page that the deck loads Spotify's player script after Start; verify with a view test.
- [ ] 3.2 Run the whole suite with the network blocked, and check the deck at 390px and 1440px with a Spotify-only card.
