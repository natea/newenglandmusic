Issue: [#74 YouTube videos aren't auto-playing on the band discovery tool](https://github.com/natea/newenglandmusic/issues/74)

## Context

`/discover` (`core/templates/core/discover.html`, `core/static/core/js/discover.js`) shows one card at a time. The first card waits for a Start press; each later card's player is loaded by the swipe, button or key that brought it up. `loadPlayer` calls `ArtistPreview.showInCard(card, button, true)`, and `youtubePlayer` in `core/static/core/js/artist_preview.js` then builds an iframe on `https://www.youtube-nocookie.com/embed/<video>` with `autoplay=1&playsinline=1`, an `allow` of `autoplay; encrypted-media; picture-in-picture; fullscreen`, and a `strict-origin-when-cross-origin` referrer policy. That is all: no `enablejsapi`, no `origin`, no messages to or from the player. `improve-band-discovery` built this, and its task 3.4, trying it by hand on real browsers, is still unchecked.

The owner says the video does not start after Start. The two earlier projects (`stagehopper`, `nola-stagehopper`, which share the same code) differ from the deck in these ways:
- the embed has `enablejsapi=1` and `origin=<page origin>` as well as `autoplay=1`, on `youtube.com` rather than `youtube-nocookie.com`;
- the page listens for messages from YouTube and, on `onReady`, posts `{"event":"command","func":"playVideo"}` to the iframe (and posts it again right after creating it);
- on iPhone it shows a thumbnail and a play button and creates the iframe only inside the tap's handler, saying Safari honours a start only if it comes straight from a tap;
- an `onError` or error codes 100, 101 or 150 swap the player for a "search YouTube" link;
- an autoplay on/off toggle sits on the card.

## Goals / Non-Goals

**Goals:** make the YouTube video of the top card start by itself after Start and after each swipe, button or key, in the browsers the owner uses, and say so plainly when it still cannot.

**Non-Goals:** Apple Music and Spotify autoplay (they load ready, by `improve-band-discovery`); the listings' players; an autoplay toggle; muted autoplay; any change to the deck's order, filters, swipe directions or saved shows.

## Decisions

### 1. Reproduce before building
The cause is not known. `autoplay=1` with an `allow` of `autoplay` is YouTube's documented way, and it should work when the iframe is created inside a visitor's click. Candidates: the player starts but the browser or YouTube refuses it for a reason the parameter cannot override; the start request is lost because the player was not ready; the iframe is created after the visitor's action has lapsed (the swipe path waits 170 ms for the slide-off animation, and Safari is strict); or the embed on `youtube-nocookie.com` behaves differently from `youtube.com`. The first task is to reproduce on the owner's browser (the owner should say which, see open question 1), and to record in this design which candidate it was and what fixed it. The tasks after it build the expected fix and stay in step with what is found. If the result contradicts the design, the design and tasks change, not just the code.

### 2. Ask through the player API as well as the address
The deck's embed gets `enablejsapi=1` and `origin`. The page listens for `message` events, accepts only those whose `source` is the top card's iframe window and whose origin is YouTube's embed host (`youtube-nocookie.com` or `youtube.com`), and on a ready report posts `playVideo` to that frame, targeting the embed's origin rather than `*`. This follows the earlier projects. It uses the documented player API's message channel directly and does not load YouTube's `iframe_api` script, so no new script is added to the page (open question 2 asks whether that is acceptable or the script is preferred).

The player must say "listening" before it sends events: the page posts `{"event":"listening"}` once the frame loads, which is what YouTube's own script does. The design's reproduction step checks this against the real embed, since the earlier projects' code did not do it and still received ready.

### 3. Know whether it is playing
Messages carry the player state (playing, paused, ended) and errors. The page keeps, per top card: ready, playing, and the timers. After ready it waits 4 seconds; if not playing it sends `playVideo` once more; 3 seconds later, if still not playing, it shows one line under the player: "Press play in the player to start the music." The line sits in the card's flow, below the player box, never over the iframe (YouTube's rules, `PRODUCTION.md`). It is a polite live region. The numbers are a first guess, checked by hand in the reproduction (open question 7 asks the owner to confirm them). If the player never reports ready (a content blocker, or the frame never answering), a fallback timer started when the frame loads shows the same line after 7 seconds, since a player that never speaks cannot be told to play; it also goes if the player later reports playing.

### 4. A video that cannot be embedded
Error 100 (not found or removed), 101 and 150 (embedding not allowed) all replace the player with a message and a link to the video or channel on YouTube, as the earlier projects swapped in a search link. A link to the video itself is used rather than a search, because the card knows the video. A deck of matched videos should seldom hit this, but `match_youtube_artists` checks embeddability only when it matches, and a video can change later.

### 5. Create the next player inside the action
Today skip, swipe and key handlers call `moveOff`, which waits 170 ms for the slide animation and then calls `advance` and `show`, which load the next player. Until `advance` runs the passed card is still the top card (`index` is unchanged) and its player keeps playing. Browsers keep a visitor's action alive for a short time, but Safari only honours a start that comes straight from a tap, so a timer in between may lose it. The change moves the swap into the handler, in this order, in one step:
1. Set a "move in progress" flag. `skip()` returns at once while it is set (today it has no guard, so a double press or a held key calls `advance` twice). The flag is cleared when the slide-off animation ends (or at once with reduced motion). A test covers a key held down and a double press.
2. Remove the passed card's player (clear its box, stop listening to its frame, clear its timers), so two players never play at once and the passed card is never told to play.
3. Advance `index`, so the next card is the top card from this moment, and the message listener treats only its frame as current.
4. Create the next card's player (`showInCard` with autoplay). `show()` must not clear or reload it: `showInCard` already skips a box whose `dataset.playing` is set, and `show()`'s clearing of non-top cards runs only for cards that are not the new top. The design names this dependency so a change to either is noticed.
5. Let the passed card slide off, as a copy under or beside the stage that holds no player, so the animation shows the card's text and image but never a second iframe.

A player in a card with `hidden` set may not load or play, so the new top card is shown (not `hidden`) in step 3, and the passed card, once its player is gone, is the only thing left to animate. The deck's markup is one card at a time, so the work is CSS and `show()` handling: the passed card is `aria-hidden` and not focusable while it animates, focus and the live region move to the new top card in step 3, and the stage keeps the height of the taller card for the 170 ms. This is the riskiest part, and the build starts with it (task 4.1) and records what it found; open question 3 covers dropping it if Start-gated first plays and key presses are enough.

Save and "Start again" already call `advance` straight from the click with no animation, so they are already inside the visitor's action and are not changed; only swipe, Skip and the arrow keys wait for a timer today. The first card already loads inside the Start press. Browser tests that count iframes (the deck tests that assert exactly one frame) wait for the animation to end, or assert on the top card's frame, since the passed card's player is gone by then and only one exists at any time.

### 6. iPhone
The Start press is already a direct tap, and the iframe is created inside it, which is what the earlier projects' iPhone thumbnail achieves, so no extra facade is built. If the reproduction shows Safari still refusing a later card, the fallback is the "Press play" line of decision 3, which exists for exactly this.

## Mocking and tests

No outside service is called by the server, and tests never touch the network. Browser tests (Playwright, `requirements-dev.txt`) route every request to YouTube's embed addresses to a stub page. The stub page is a small local page that, when the test asks, posts the messages YouTube's player would (ready, playing, error 101) to its parent and records the commands it receives (`playVideo`), so a test asserts the iframe's `src` and `allow`, the commands sent, the "press play" line and the unplayable message, with a fake clock for the 4 and 3 second waits. Tests cannot hear sound, so whether real browsers play is checked by hand and recorded in the tasks. View and template tests are unchanged apart from the address strings. The existing tests that assert the exact address `...?autoplay=1&playsinline=1` change to the new address.

## Risks / Trade-offs

- **Autoplay stays best effort.** Browser policy decides. The "press play" line is the fallback, and it is what the deck does today plus a hint.
- **Terms.** The player API is YouTube's documented way to control an embed; nothing is drawn over the player and only one is asked to play at once. The player API's channel is what `PRODUCTION.md` calls the "YouTube Embedded Player API", which it says to leave off in the Google Cloud console because the player is a plain iframe. That switch governs API-key use, not an embed's own message channel, so nothing is switched on, but that "YouTube play buttons" paragraph is updated to say so (task 5.2). This is read again against the current terms, as `improve-band-discovery` recorded, before the build. The listings are unchanged.
- **Privacy.** `enablejsapi` and `origin` add no request: the same embed loads after the visitor's action. They tell YouTube which site embeds it, as the referrer policy already does.
- **Stubbed messages are our guess of YouTube's.** The stub copies the earlier projects' working messages; a real browser check is what proves it.

## Open Questions

1. **Which browser and device?** On what browser, version and device did the owner see the video not start (phone or desktop; Chrome, Safari or other), on the first card only or later ones too, and with an ad blocker or content blocker on? The reproduction starts from the answer.
2. **API script or raw messages?** The earlier projects post messages directly. YouTube's `iframe_api` script is its documented route but is one more script from YouTube. This design builds the raw messages; is that acceptable?
3. **Later cards.** If making the next card displayable early (decision 5) proves unreliable, should the deck instead play only after a key or tap on a "Next" control, or keep today's timing?
4. **An autoplay toggle?** The earlier projects have one. Add it to the deck, or leave autoplay always on after Start?
5. **`youtube.com` or `youtube-nocookie.com`?** The deck uses the privacy-enhanced host, the earlier projects `youtube.com`. If the reproduction shows the host matters, which wins, privacy or autoplay?
6. **Needs a design round?** The "press play" line and the unplayable message are small, so no screens are sketched. Say if a sketch is wanted.
7. **The waits.** Are 4 seconds to retry and 3 more before the "press play" line (7 seconds from load if the player never reports ready) acceptable, or should the line come sooner or later?

## Archiving

`improve-band-discovery` has a scenario "The deck's player may autoplay after a visitor action" that says the deck's `src` is the same embed with only `autoplay=1` added, and one saying the listing's player does not autoplay. This change's `youtube-artist-preview` requirement adds `enablejsapi=1` and `origin` to the deck's `src`. When archiving, reword the older scenario to mention them or drop it, so two scenarios do not describe the deck's `src` differently. Archive `add-band-discovery-swipe` first, then `improve-band-discovery`, then this change.
