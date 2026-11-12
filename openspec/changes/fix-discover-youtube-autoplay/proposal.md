Issue: [#74 YouTube videos aren't auto-playing on the band discovery tool](https://github.com/natea/newenglandmusic/issues/74)

Issue: [#74 YouTube videos aren't auto-playing on the band discovery tool](https://github.com/natea/newenglandmusic/issues/74)

## Why

On `/discover`, the owner reports that the YouTube video does not start by itself, even after pressing Start. This is a follow-up to #63, whose change (`improve-band-discovery`) already loads the top card's player with `autoplay=1&playsinline=1` and an `allow` that includes `autoplay`, from the handler of the Start press, swipe, button or key. That is the whole of what the site does today, and it is not enough in the owner's browser. The earlier change also left its by-hand check on real phones and desktops (its task 3.4) unrecorded, so nothing says which browsers it works in.

The owner points to two earlier projects, `stagehopper` and `nola-stagehopper`. Both play YouTube differently from the deck. They add `enablejsapi=1` and the page's `origin` to the embed address, listen for the player's messages, and send it a `playVideo` command when it reports ready (and again whenever autoplay is switched on), rather than relying on the `autoplay=1` parameter alone. On iPhone they show a thumbnail with a play button first and load the player only when that is tapped, because Safari only honours a start that comes straight from a tap. If a video reports an error they swap it for a "search YouTube" link. They also have an on-card autoplay on/off toggle.

## What Changes

- **Start the player through YouTube's player API as well as the address.** The deck's YouTube embed gets `enablejsapi=1` and the site's `origin`. When the player reports ready, the page sends it `playVideo`, as the two earlier projects do. `autoplay=1` stays as the first attempt. This is for the deck only; the listings' players stay as they are.
- **Hear what the player says.** The page listens to the deck's player for "ready", for errors (a video that cannot be embedded or has been removed), and for whether it is playing. This lets the deck try the start once more if it did not take, and tell the visitor when it did not.
- **When playing cannot start, say so and leave the player alone.** If the player has not started a few seconds after it was asked to, a short line below it (never over it, which YouTube's rules forbid) tells the visitor to press play in the player. If the player never answers at all, the same line comes after 7 seconds. If the video cannot be embedded, the card says so and links to the video on YouTube.
- **Start each card from the visitor's own action.** The next card's player is created in the same step as the swipe, Skip press or arrow key that brought it up, not after the card's slide-off animation, so the browser still counts the visitor's action (Safari is the strictest). The passed card's player is removed in that step, so only one plays, and a double press moves once. The first card's Start press, Save and "Start again" already act in the visitor's action.
- **Find out why it fails first.** Before building, the real failure is reproduced in the browsers it affects and the cause recorded in the design. The change fixes what that finds. The two earlier projects' approach is the expected fix, not a certainty (see the design's open questions).
- **Autoplay on/off.** The earlier projects have a toggle for autoplay. Whether the deck should have one is an open question; this change does not add it.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `band-discovery`: how the top card's YouTube player is started and checked (player API, ready, retry, "press play" line, unplayable video), and that each new card's player is created in the visitor's own action. This capability is defined by `add-band-discovery-swipe` and amended by `improve-band-discovery`, neither of which is archived yet, so this change adds requirements and does not rewrite theirs, and is archived after both.
- `youtube-artist-preview`: the deck's player may also use `enablejsapi=1`, the site's `origin` and player messages; the listings' players still carry none of these.

## Impact

- **Code:** `core/static/core/js/artist_preview.js` (the YouTube player's address and, for the deck, its message handling), `core/static/core/js/discover.js` (creating the next player inside the visitor's action, the "press play" line, the unplayable-video state), `core/templates/core/discover.html` and `core/static/scss/discover.scss` only for that one line, and the deck's browser tests (`core/tests/test_discover_browser.py`), several of which assert the exact embed address and must change.
- **No model or schema change, no migration, no new external API call, no paid call, no new key.** The player API is a message channel to the embed the deck already loads. `PRODUCTION.md` says to leave the YouTube Embedded Player API off in the Cloud console because the player is a plain iframe; that switch is not needed for this channel, and the paragraph is updated to say so. If open question 5 ends in switching to `youtube.com`, `privacy.html` and its render test change too. YouTube's separate `iframe_api` script is not needed unless the design's open question 2 says otherwise.
- **Screens:** one short line under the player, and a message in place of an unplayable video. Both are small enough to need no design round, so no `needs-design` label; the first open question lets the owner ask for one.
- **Outside this change:** Apple Music and Spotify autoplay (they still load ready, as `improve-band-discovery` decided), the listings' players, the swipe directions, the filters and the deck's order.
