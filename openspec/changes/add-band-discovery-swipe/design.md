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
The view renders every card into the page (a deck of the site's live acts with upcoming shows, in a random order chosen per visit, which the page must not cache; tests seed the order) and a small script moves through them. Each card carries its shows as data (event ID, date, time, venue, town), so the picker needs no request. The no-JavaScript page is the same markup, just stacked. *Alternative:* a JSON endpoint fetched card by card. Rejected for now: more moving parts, and the deck is small enough to render at once. The deck is built in bulk (prefetch performers and events, one lookup per link table), not a query set per act. The events come through the approved-only `Event.objects` (a prefetch with `Prefetch(..., queryset=Event.objects...)`, not the default related manager, which would leak unapproved events), with `is_cancelled=False` and the same start-of-today bound as `upcoming_shows` (`beginning_of_day(get_current_new_york_datetime())`), so the deck and the band page agree on "upcoming". If the act count makes the page heavy, cap the deck (open question 4). Venue, town and time use the event's venue and its override fields, and cope with a missing venue. Acts that are both an artist and a band, or share a show through members, may give near-duplicate cards; accepted for now. The no-JavaScript bookmarks use `next=/discover` with a per-show anchor, so each save returns to that show.

### 2. A card stands for an act; the show is chosen at the picker
Per the thread. The picker's confirm applies a change to the current cookie in one write, never replacing it: it adds the newly ticked IDs and removes only the unticked IDs of that act's shows, keeping every other saved show, newest first, with the same limit and dedupe as `saved_shows.js`. It shares that code rather than copying it: `saved_shows.js` keeps its cookie code private, so it exposes a small API of the shape `window.SavedShows.apply(add, remove)` that reads the current cookie, writes the result, and re-renders the header count and the `.save` buttons. Saved shows that are now past or cancelled are not in the picker, so they can't be unticked there; they stay saved until `/saved` prunes them. Already-saved shows are ticked when the picker opens and unticking one removes it on confirm, so the picker is a full view of that act's shows (open question 6). Confirming with the ticks unchanged from what was saved changes nothing and leaves the picker open; so a visitor can remove an act's last saved show by unticking it and confirming. Nothing about acts is stored; the saved list stays shows only.

### 3. Deck membership
Live acts (`needs_review` false) with at least one approved event from the start of today, found through `EventPerformer`. It ignores the remembered area filter, as `/saved` does. Cancelled shows (`Event.is_cancelled`) do not count: an act with only cancelled upcoming shows is left out, and cancelled shows are left out of the card's next show and the picker. The band page's `upcoming_shows` does not filter them today, so the deck uses its own filter rather than changing the band page.

### 4. Play buttons from an act's name
The listings build buttons from an event's names. The card needs them from one act's name, through the same link tables and the same `*_PREVIEWS` switches, so a card never shows a button the listing wouldn't. That is a small act-level entry point beside the event one in `core/artist_previews.py`, reusing the same candidate-key and button-building functions (the act's name matched by `normalize`), not a second matching path. The card uses the `.artist-previews` class and data attributes the click handler expects, and a swipe ignores pointer events that start inside the open player. The listing's functions take an event and fall back on duo and occasion names; the card matches the act's own name exactly and doesn't reproduce those fallbacks, so it may show fewer buttons than a listing for the same act. The existing click handler opens the embedded player; the card must make room for it and must not swipe when the visitor is using the player.

### 5. Gestures, keys and accessibility
Pointer events drive the swipe with a distance threshold; a short drag snaps back. Buttons and arrow keys do the same actions. The card region is a live region so the new act's name is announced. The picker is a dialog with focus kept inside and returned to the card on close. Motion respects reduced-motion settings.

### 6. Screens
The deck, card and picker are new, so the change is labelled `needs-design`; the sketch round decides layout, how the player fits, and how the end-of-deck state looks. Layout belongs to that round, not to this spec.

### Mocking services in tests
No outside service is called by this change, and tests never touch the network. Spotify, Apple Music and YouTube are represented by creating `SpotifyArtistLink`, `AppleMusicArtistLink` and `YouTubeArtistLink` rows directly (the same way the existing preview tests do) and setting the `*_PREVIEWS` switches; Wikimedia Commons photo URLs are built, never fetched, as on the band page. The embedded players are never loaded: browser tests assert only the buttons' presence and, on click, that the player's iframe is created, with outbound requests blocked or routed to a stub. Swipe, picker and cookie behavior are covered with the existing Playwright setup (`requirements-dev.txt`), and the server side (deck membership, card content, no-JavaScript page, menu link) with Django `TestCase`.

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
6. **Removing by unticking.** The thread only asked to pick shows to save. This proposal also lets unticking a saved show remove it, so the picker is a full view. Should the picker only add, showing saved shows marked "Saved" and not ticked?

## Sketches

Three options for the deck, card and picker (1440×900):

- [Option A](sketches/a.html): **Index card and side picker.** One act-tab index card, the site's own idiom, with the show picker opening beside it so the card stays in view while you tick shows. *Risk:* side by side needs width; on phones the picker must cover the card, so the desktop view is not the mobile view.
- [Option B](sketches/b.html): **Split view, shows always visible.** The act's shows sit beside the card with all ticked, so a right swipe is one step and no picker dialog is needed. *Risk:* it feels more like a list than a swipe game, and pre-ticking could save shows by accident.
- [Option C](sketches/c.html): **Photo stack with bottom sheet.** A big-photo card stack with peeking cards feels like a swipe game, and a bottom sheet holds the picker. *Risk:* it leans on photos many acts lack, departs from the text-first look, and gives the embedded player little room.
