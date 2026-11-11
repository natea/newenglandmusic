Issue: [#26 build a tinder-style band discovery tool on the site](https://github.com/natea/newenglandmusic/issues/26)

## Context

- Acts are `Artist` and `Band` (both `MusicAct`); a held act has `needs_review`. `EventPerformer` links approved events to acts. The band page already finds an act's upcoming approved shows (`upcoming_shows` in `core/views/act_page.py`), its photo and credit, and its town.
- Play buttons are baked into each event from the event's artist names (`core/artist_previews.py`): `SpotifyArtistLink`, `AppleMusicArtistLink` and `YouTubeArtistLink` rows keyed by normalized name. `core/js/artist_preview.js` opens the embedded player on click only.
- Saved shows are the `saved_shows` cookie of event IDs, newest first, at most 300 (`core/saved_shows.py`, `core/js/saved_shows.js`, `/saved`, `/saved/toggle/<id>`). It holds events, not acts.
- See proposal.md for why. The issue thread decided: one card per band, a right swipe lets the visitor pick which of its shows to save (more than one allowed), saving goes into the existing saved shows, and acts with no upcoming show can be left out.

## Goals / Non-Goals

**Goals:** a card deck that turns a taste of a band into saved shows using what exists; no new storage, accounts or paid calls.

**Non-Goals:** recommendations or ranking by taste; a shareable playlist or schedule; showing shows "near me" as a feature of its own; remembering passes; an account or syncing across devices; changing how saved shows work.

## Decisions

### 1. Deck built on the server, swiped in the browser
The view renders every card into the page (a deck of the site's live acts with upcoming shows, in a random order chosen per visit, which the page must not cache; tests seed the order) and a small script moves through them. Each card carries its shows as data (event ID, date, time, venue, town), so the picker needs no request. The no-JavaScript page is the same markup, just stacked. *Alternative:* a JSON endpoint fetched card by card. Rejected for now: more moving parts, and the deck is small enough to render at once. The deck is built in bulk (prefetch performers and events, one lookup per link table), not a query set per act. The events come through the approved-only `Event.objects` (a prefetch with `Prefetch(..., queryset=Event.objects...)`, not the default related manager, which would leak unapproved events), with `is_cancelled=False` and the same start-of-today bound as `upcoming_shows` (`beginning_of_day(get_current_new_york_datetime())`), so the deck and the band page agree on "upcoming". If the act count makes the page heavy, cap the deck (open question 4). Venue, town and time use the event's venue and its override fields, and cope with a missing venue. Acts that are both an artist and a band, or share a show through members, may give near-duplicate cards; accepted for now. `actions_html` hard-codes the anchor `#event-{pk}`, so it gains an optional anchor argument (default unchanged). The no-JavaScript list is beyond the thread but follows the site's bookmark idiom. The no-JavaScript bookmarks use `next=/discover` with an anchor made of the card (act kind and slug) and the event ID, for example `bands-belly-event-42`, so a show on two cards has two different anchors and each save returns to its own card. The page must not be shared-cacheable (`Cache-Control: private`/`no-store`) because the random order and the no-JavaScript bookmarks, which the server draws saved or not from the `saved_shows` cookie, differ per visitor. The route is placed above any catch-all pattern, and `/discover/` is handled like `/bands`.

### 2. A card stands for an act; the show is chosen at the picker
Per the thread. The picker's confirm applies a change to the current cookie in one write, never replacing it: it adds the newly ticked IDs and removes only the unticked IDs of that act's shows, keeping every other saved show, newest first, with the same limit and dedupe as `saved_shows.js`. It shares that code rather than copying it: `saved_shows.js` keeps its cookie code private, so it exposes a small API of the shape `window.SavedShows.apply(add, remove)` that reads the current cookie, writes the result, and re-renders the header count and the `.save` buttons. Saved shows that are now past or cancelled are not in the picker, so they can't be unticked there; they stay saved: `/saved` prunes only past, deleted and unapproved shows, not cancelled ones, so a cancelled saved show stays until it is past. Already-saved shows are ticked when the picker opens and unticking one removes it on confirm, so the picker is a full view of that act's shows (open question 8). Confirming with the ticks unchanged from what was saved changes nothing and leaves the picker open; so a visitor can remove an act's last saved show by unticking it and confirming. Nothing about acts is stored; the saved list stays shows only.

### 3. Deck membership
Live acts (`needs_review` false) with at least one approved event from the start of today, found through `EventPerformer`. It ignores the remembered area filter, as `/saved` does. Cancelled shows (`Event.is_cancelled`) do not count: an act with only cancelled upcoming shows is left out, and cancelled shows are left out of the card's next show and the picker. The band page's `upcoming_shows` does not filter them today, so the deck uses its own filter rather than changing the band page.

### 4. Play buttons and the top card's player
The top card plays in place of the photo: the act's YouTube video if matched, else Apple Music, else Spotify, else the photo. Spotify is the last option, both in the buttons' order and in which player loads (feedback: a reader wanted it last, not removed). An act matched on Spotify alone gets its Spotify player. The listings keep their buttons unchanged; the Discover entry point returns YouTube, Apple Music, Spotify in that order. Only the top card has a player; the script creates it when a card comes to the top (on arrival, including the first card) and removes it on skip or add, so cards underneath load nothing. The player loads ready but not playing, and the visitor presses its own play control; the page never starts sound. That is the one rule in the spec and tasks. Whether autoplay is wanted, and whether YouTube's terms allow it, is open question 6 and is not built here. Each play button shows its service's icon, drawn from the page's shared icon sprite (`core/templates/core/icons.html`) in the service's colours, next to its name, so the buttons are told apart by more than text.

#### Play buttons from an act's name
The listings build buttons from an event's names. The card needs them from one act's name, through the same link tables and the same `*_PREVIEWS` switches, so a card never shows a button the listing wouldn't, and the Spotify button and player follow the same `SPOTIFY` link table and switch. That is a small act-level entry point beside the event one in `core/artist_previews.py`, reusing the same candidate-key and button-building functions (the act's name matched by `normalize`), not a second matching path. The card's buttons use the `.artist-previews` class and data attributes the click handler expects, and a swipe ignores pointer events that start inside the player. The listing's functions take an event and fall back on duo and occasion names; the card matches the act's own name exactly and doesn't reproduce those fallbacks, so it may show fewer buttons than a listing for the same act. The existing click handler (`artist_preview.js`) allows one `.artist-player` on the page and toggles it off when its own button is pressed again, and its builders are private and fixed in height (152 px Spotify, 175 px Apple). So the change exposes the builders with a height and gives the card its own rule: pressing one of the card's play buttons replaces the card's player with that service's, and the listings' behavior is unchanged. The card must make room for the player and must not swipe when the visitor is using the player.

#### The player's size and what may cross it
YouTube's Required Minimum Functionality rules (`PRODUCTION.md`, YouTube section) forbid changing the player or putting anything over it, and require at least 200 × 200 px. So the card gives the player its own box, at least 200 × 200 px at phone widths for every service (the listing's Spotify player is only 152 px high, so the card sizes players per service and does not reuse that height, Spotify's included). The "Skip" and "Add" labels, buttons, the sway and card text sit beside or below that box, never over it. The sway moves the whole card, which moves the player as one piece without covering it; if the design round finds that unacceptable it can stop the sway while a video is shown. A swipe starts only on the card outside the player box (its name and show area), and pointer events that start in the player are left to it.

### 5. Gestures, keys and accessibility
On the first card a sway animation with "Skip" and "Add" labels teaches the swipe, until the visitor first swipes or presses a button; it is not stored, and under reduced motion only the labels show. The picker opens only after a right swipe, the add button or the right arrow, never with the card. Each show's row is one label around its checkbox, so tapping anywhere in it ticks it; a Save button ("Save N shows") applies the ticks, and ticking alone saves nothing. Pointer events drive the swipe with a distance threshold; a short drag snaps back. Buttons and arrow keys do the same actions. The card region is a live region so the new act's name is announced. The picker is a dialog with focus kept inside and returned to the card on close. Motion respects reduced-motion settings.

### 6. The site's header
`/discover` extends `core/base.html` like the other pages, so it gets the masthead, search, burger and footer menus from it, with the menu items from the admin; the page defines no header. The sketch had drawn its own header, which is corrected to match the home page. Making that consistency a check across all pages is outside this change (file its own issue if wanted).

### 7. The menu link
The "Discover bands" menu item is not from the issue thread; it follows the "Bands & artists" precedent (`0102`) and is needed for visitors to reach the page. Editors can hide it in the admin.

### 8. Screens
The deck, card and picker are new, so the change is labelled `needs-design`; the sketch round decides layout, how the player fits, and how the end-of-deck state looks. Layout belongs to that round, not to this spec.

### Mocking services in tests
Migration `0103` is the next number now; check the dependency chain at apply time, since other open changes may claim it.

No outside service is called by this change, and tests never touch the network. Spotify, Apple Music and YouTube are represented by creating `SpotifyArtistLink`, `AppleMusicArtistLink` and `YouTubeArtistLink` rows directly (the same way the existing preview tests do) and setting the `*_PREVIEWS` switches; Wikimedia Commons photo URLs are built, never fetched, as on the band page. The embedded players, Spotify's included, are never loaded: browser tests assert only the buttons' presence and, on click, that the player's iframe is created, with outbound requests blocked or routed to a stub. Swipe, picker and cookie behavior are covered with the existing Playwright setup (`requirements-dev.txt`), and the server side (deck membership, card content, no-JavaScript page, menu link) with Django `TestCase`.

## Risks / Trade-offs

- A large deck rendered at once could make the page heavy; mitigated by a cap if needed.
- `saved_shows.js` watches the whole document and re-scans every `.save` button when elements are added, so a big deck rendered at once, or cards swapped in and out, wakes it often. It is throttled to one frame, but the deck cap (open question 4) matters for this.
- Passes aren't remembered, so a visitor who returns sees acts they already dismissed. Accepted for a first version; see open question 3.
- Acts only appear if their events are linked to them (`EventPerformer`); acts whose names don't match an event's text won't be discoverable. Deck size depends on how many are linked.

## Open Questions

1. **What to copy from the reference site.** The issue says "modeled after" the New Orleans Jazz Fest discovery site, but that site wasn't inspected for this proposal, so its features (filters, a lineup or schedule view, how its cards look) are not assumed. Nate should say what to carry over; the design round can then match it.
2. **Area.** Should the deck follow the visitor's remembered area filter (so a Vermont visitor sees Vermont acts) rather than the whole region as proposed here?
3. **Remembering passes.** Should an act the visitor passed stay out of the deck on later visits? That needs a new cookie or stored state, which this proposal avoids.
4. **Deck size and order.** Random per visit is assumed. Should it be soonest-show-first, and should it be capped (for example at 50 cards)?
5. **Acts already fully saved.** Should an act whose shows are all saved still appear in the deck? Assumed yes, with its saved shows ticked.
6. **Sound.** Should the top card's player start with sound on its own where the browser allows it, or start muted? Built here: it never starts by itself. Whether YouTube's terms allow autoplay has not been checked; it must be before this is changed.
7. **Service icons.** Apple and YouTube set rules for using their logos; the icons should follow them (plain marks, no alteration). Should the same icons also go on the listings' play buttons? Assumed: only the Discover card now.
8. **Removing by unticking.** The thread only asked to pick shows to save. This proposal also lets unticking a saved show remove it, so the picker is a full view. Should the picker only add, showing saved shows marked "Saved" and not ticked?
9. **Spotify's rank.** Built here: Spotify is the last button and the last player to be tried, and a Spotify-only act plays on Spotify. Should the listings' button order also put it last? Today it is unchanged there.
10. **Bandcamp player.** See "Bandcamp embedded player" below. Should a separate issue and proposal be opened for it?

## Bandcamp embedded player (investigated, not built here)

Bandcamp's embedded player is an iframe whose address carries the numeric album or track ID (and options such as size and colours), shown to an artist or label in the share/embed dialog on their own page. The help article linked in the thread could not be fetched while writing this, so the details here come from the repository's own notes and general knowledge, and should be checked against it before a proposal. What it would take:

- **The ID is the problem.** The site stores only a Bandcamp page URL per act (`Artist.bandcamp_url`, `core/artists.py`). Nothing in a page URL gives the numeric ID. Getting it from the page would mean requesting Bandcamp pages, which `PRODUCTION.md` says its acceptable use policy forbids, and Bandcamp has no public API for it. So the ID cannot be found by a command or at deploy time.
- **A workable route:** an editor pastes the act's embed code (or just the ID and kind, album or track) from Bandcamp's own share dialog into the admin, and the site stores that ID. That is a model field, so it is a schema change and needs its own OpenSpec proposal and Nate's go-ahead, plus a rule on who may add it and a check that the address is a Bandcamp embed. Artists could also send it by email, as they do for photos.
- **On the card:** the player would join the order YouTube, Apple Music, Spotify, Bandcamp or sit where that issue decides (a question for that issue, not open question 10, which only asks whether to file it), at least 200 × 200 px like the others, loaded only on the top card and never autostarted. A button with a Bandcamp icon would follow the page's icon rules.
- **Few acts would have one**, since it is hand-entered, so it would not change who is in the deck.

Recommendation: file it as its own issue, "Embedded Bandcamp player for acts", and leave it out of this change. This change adds no field, no outside request and no Bandcamp code.

## Sketches

The first round's feedback chose option C and the others were deleted; round 2 revises it to put Spotify back, last. One option for the deck, card and picker (1440×900):

- [Option C](sketches/c.html): **Video card stack with bottom sheet.** A card stack with peeking cards feels like a swipe game: the card plays the act's video, else its Apple Music player, else Spotify's, an animated hint teaches the swipe, and a bottom sheet with whole-row tick targets and a Save button holds the picker. *Risk:* players need a tap or a muted start to play, browsers decide whether sound starts on its own, and the embedded player leaves little room on a phone.
