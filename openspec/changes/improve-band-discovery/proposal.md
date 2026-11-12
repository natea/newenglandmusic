Issue: [#63 some improvements to the tinder-style band discovery tool](https://github.com/natea/newenglandmusic/issues/63)

Issue: [#63 some improvements to the tinder-style band discovery feature](https://github.com/natea/newenglandmusic/issues/63)

## Why

The band discovery deck at `/discover` (built by the still-open change `add-band-discovery-swipe`) works, but four things hold it back. A visitor has to press play on every card, which takes the "flip and listen" feel out of it. Acts with nothing to play still appear, as a photo and a name with no music. The deck shows every act in the Northeast, while the event listing lets a visitor narrow to their own region, state or metro. And the issue says a right swipe skips an act when it should add its shows to the visitor's schedule.

## What Changes

- **Right is add, left is skip.** The code already does this (right swipe, the "Add" button and the right arrow open the show picker; left swipe, "Skip" and the left arrow pass), so this is not expected to change behaviour. The change pins the directions down with a touch-gesture test on a phone-sized screen, and the design records what to do if the reporter's device turns out to behave the other way round. Whether the labels should read "Add to my schedule" is an open question.
- **Music starts by itself.** When a card comes to the top after the visitor's own action (a swipe, a button, an arrow key, or a first "Start" press on the deck), its player is created asking the service to start playing, within what browsers and each service allow. Where a service cannot be started by the page, the card stays ready for the visitor to press play, as today.
- **Only acts with something to play.** An act with no YouTube, Apple Music or Spotify match is left out of the deck, in the JavaScript deck and the no-JavaScript list alike. A photo no longer stands in for a player, so cards stop showing photos.
- **Filters like the listing's.** `/discover` gets the same Region, State and Metro Area filters, chosen with the same `region`, `state` and `metro` query parameters (and the metro's towns and neighborhoods the listing already offers), working without JavaScript. The deck holds acts with an upcoming show at a venue in the chosen areas, and a card and its picker list only those shows. The deck uses the same remembered filter as the listing. A genre filter is left for later, once there is genre data to filter on.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `youtube-artist-preview`: its player may autoplay in the discovery deck only, after a visitor action; the listings' players stay press-to-play.
- `band-discovery`: who is in the deck (only acts with media; narrowed by the area filter), what a card shows (no photo), how the top card's player starts, and when the swipe hint begins and what "start again" does. This capability is defined by `add-band-discovery-swipe`, which has not been archived yet, so that change is archived first.

## Impact

- **Code:** `core/views/discover.py` (leave out acts with no media, apply the area filter and its cookie, narrow each card's shows), `core/templates/core/discover.html` (the filter form, no photo, an empty state that mentions the filter, a start control), `core/static/core/js/discover.js` and `core/static/core/js/artist_preview.js` (create the player asking to autoplay, only after a visitor action), the deck's styles, the shared filter context (extracted from the listing's view), and the existing deck tests and their fixture (media-less acts). The filter form partial and `core/geo_filters.py` are reused, and the listing's behaviour does not change.
- **No model or schema change, no migration, no new external API or paid call.** Autoplay is a request made inside the visitor's browser to the same embedded players the deck already loads. If Spotify's own iFrame API script is needed to start its player, that is a new script loaded from Spotify, decided in the design's open questions before it is built.
- **Screens:** the Start control, the filter form on the deck and the changed empty states are screen changes, so this needs a design round (`needs-design`).
- **Reverses a rule of `add-band-discovery-swipe`:** its deck ignored the remembered area filter and never changed it; this change makes the deck follow it.
- **Outside this change:** a genre filter (genres exist on acts from MusicBrainz but are sparse, and the listing has no genre filter yet), remembering passed acts, and a Bandcamp player.
