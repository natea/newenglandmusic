Issue: [#104 YouTube videos don't play on mobile](https://github.com/natea/newenglandmusic/issues/104)

Archive `add-band-discovery-swipe` and `improve-band-discovery` before applying this change, since it builds on the deck they describe.

Issue: [#104 YouTube videos don't play on mobile](https://github.com/natea/newenglandmusic/issues/104)

## 1. Find a route that works on iOS

- [ ] 1.1 Spike on a real iPhone (Chrome and Safari) with the deck: try muted autoplay and the IFrame Player API from the Start tap and from a swipe, and record in the design which works, resolving open questions 1, 3 and 5.
- [ ] 1.2 Update the proposal, design and spec to the result before building (including amending "The deck starts a YouTube video on iPhone" if no route works).

## 2. Start the video on iOS

- [ ] 2.1 Change `youtubePlayer` / `showInCard` and `discover.js` to use the chosen route for iOS only, leaving desktop's `autoplay=1` and the listings' players as they are, and nothing loaded from YouTube before Start.
- [ ] 2.2 Tests (browser, with the YouTube embed, script and thumbnail routed to stubs; iPhone tests assert the `enablejsapi` address, desktop tests the unchanged one): "Start plays the first video on iPhone", "A later card plays on iPhone", "Desktop is unchanged", "The listing is untouched", "Before Start" (which also checks no request to the script address), using an iPhone device profile.

## 3. The tap-to-play note

- [ ] 3.1 Add the note beside (not over) the player when the video was asked to play and hasn't started within the wait, removed when it plays; style it in `discover.scss` and check it at 390 px wide.
- [ ] 3.2 Tests with the stubbed player's state: "Phone refuses", "Video starts", "Ready cards" (Apple Music and Spotify show no note).

## 4. Records

- [ ] 4.1 Say that the YouTube IFrame API script loads on the deck's iPhone path (unconditional) on the privacy page and in `PRODUCTION.md`, with a test that the page mentions it.
- [ ] 4.2 Try it by hand on an iPhone and on desktop Chrome, and record the results in the design.
