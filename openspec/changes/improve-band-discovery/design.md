Issue: [#63 some improvements to the tinder-style band discovery feature](https://github.com/natea/newenglandmusic/issues/63)

## Context

- The deck is `core/views/discover.py` (cards built in bulk from `EventPerformer` rows of approved, uncancelled, upcoming shows), `core/templates/core/discover.html` and `core/static/core/js/discover.js`. Its change, `add-band-discovery-swipe`, is built but not archived (its task 4.1, the design review, is open), and its spec is not yet in `openspec/specs/`. This change modifies that spec, so **that change must be archived first**; until then `openspec validate` notes that the delta cannot be archived.
- The listing's filter is `core/geo_filters.py`: `parse_geo_filter`, `geo_filter_for_request` (URL wins, else the `geo_filter` cookie, which redirects), `apply_cookie_action`, `GeoFilter.q(prefix=...)`, `metro_groups`, plus the form `core/templates/core/geo_filter_form.html` and the context `core/views/index.py` builds for it. `/discover` today ignores it.
- Play buttons come from `act_previews` (`core/artist_previews.py`), which returns an entry only for names matched on a service with its switch and credentials on. `Card.has_player` already means "has media".
- `core/static/core/js/artist_preview.js` builds the players. YouTube's embed has no `autoplay` parameter and an `allow` of `encrypted-media; picture-in-picture; fullscreen` (a comment says "no autoplay"). Spotify's and Apple Music's iframes already carry `allow="autoplay…"` but no way to start them.
- The issue's reference, the nolajazzfest.stagehopper.app site, could not be inspected while writing this, so how it starts its players is not assumed (open question 1).

## Goals / Non-Goals

**Goals:** a deck ordered soonest show first that starts music without a tap where browsers permit, holds only acts with something to play, narrows by the listing's area filters, and has right = add, left = skip.

**Non-Goals:** a genre filter (open question 4); remembering passed acts; a Bandcamp player; changing the listing's filter or the saved shows; muting or volume controls of our own (the services' players have their own).

## Decisions

### 1. Swipe direction: confirm, don't rewrite
`discover.js` already maps a right drag, the "Add" button and ArrowRight to the picker, and a left drag, "Skip" and ArrowLeft to a pass; the hint reads "← Skip" and "Add →". The issue says the opposite is happening, which this reading of the code does not explain. So the work is a test, not a rewrite: a browser test drives touch events on a phone-sized screen (the existing swipe tests use a mouse) and pins both directions. If that test, or the reporter's device, shows the reverse, the cause is found and fixed under this requirement (a likely suspect is a touch or RTL-specific path), and the finding recorded here. The label wording ("Add" against "Add to my schedule") is open question 2.

### 2. Autoplay: gate the first card, then play on each action
Browsers block sound that starts without a visitor action. A visitor's swipe, tap or key press is such an action, but the page load that shows the first card is not. So the deck opens with a "Start" control laid over our own placeholder (the video's thumbnail, or a plain dark box), never over the player itself: YouTube's rules forbid anything over its player (`PRODUCTION.md`), so the placeholder and control are removed when the player loads. Pressing it counts as the action and loads the first card's player. Later cards load from the handlers of the swipe, button or key, in the same event turn, so the action carries over. The alternative, muted autoplay of the first card, needs an unmute tap and is a worse experience; it stays the fallback if the Start control is rejected in the design round (open question 3).

How each service is asked to start, to be verified against the service's documentation when building (not assumed here):
- **YouTube's terms (checked before building, task 3.0):** the main spec `youtube-artist-preview` says its player SHALL NOT autoplay, a deliberate compliance choice (`PRODUCTION.md`). This change therefore also modifies that spec, allowing `autoplay=1` for the deck only, after the visitor's own Start, swipe, button or key. The embedded player's `autoplay` parameter is documented; the check is whether YouTube's current developer policies allow it, recorded here before the build. If they do not, the fallback is open question 3.
- **YouTube:** the embed URL gets `autoplay=1` (and `playsinline=1` for iOS), and the iframe's `allow` gains `autoplay`. This is the documented way. The listing's players are unchanged (they stay press-to-play), so `youtubePlayer` takes an option rather than changing for everyone.
- **Spotify:** the plain iframe has no start parameter. Starting it from the page needs Spotify's iFrame API script and its controller's `play()`. That is an extra script loaded from Spotify, so it is open question 5; without it a Spotify-only card stays ready, with its own play control.
- **Apple Music:** no documented way for the page to start the embed was found in the repository's notes. It stays ready for a press unless the build finds one.

The Start control sets the hint's start: the swaying hint runs only after Start, and "start again" at the end of the deck counts as the visitor's action (no second Start). The no-JavaScript list is unaffected. `prefers-reduced-motion` affects movement, not sound, so it changes nothing here. While the picker is open the top card's player keeps playing: the visitor is choosing shows by what they hear. Saving or skipping removes the player and its sound, then starts the next.

### 3. Only acts with media
Existing tests assume media-less acts appear, so the fixture gets a default link (task 1.2).
The view already computes each card's previews after building cards from performances. Acts whose previews are empty are now dropped there, so one rule serves the deck and the no-JavaScript list, and the photo code (`photo_of`, `Card.photo`, the template figure) is removed because no card can lack a player. The cost does not grow: `act_previews` is already one query per service for all names. With the switches or credentials off in an environment the deck is empty, and says so as it does now. Acts keep their pages and listings; only the deck changes.

### 4. Filters: reuse the listing's, deck-side
The view resolves the filter first, before any deck work, so a request that redirects (cookie or clear) never builds the deck; it calls `geo_filter_for_request` and `apply_cookie_action` like `core/views/index.py`, passes the same context to the shared `geo_filter_form.html` (its `action` is `request.path`, so it posts to `/discover`), and adds `geo_filter.q(prefix="event__venue__")` to the performance query, so the venue fields are matched the same way as on the listing. The shows on a card are those the query returns, so a card and its picker list only shows in the area, and an act with none in the area is not in the deck. The query uses one extra join, with no per-act queries; the existing `assertNumQueries` bound stays.

The deck follows the **same remembered filter** as the listing (one cookie, redirect when a bare `/discover` is opened). That reverses the rule in `add-band-discovery-swipe` ("the deck ignores the remembered area filter and never changes it") and its test, which are changed here. The reasoning: the issue asks for filtering "the same way" as the listing, and a visitor who narrowed to Vermont would expect the deck to agree. The cost is that a bare `/discover` link may redirect; open question 6 asks whether the deck should rather ignore the cookie and take only the URL.

Changing a filter reloads the page, which restarts the deck (ordered soonest first again, the Start control again). The listing's form auto-submits with an inline script that is part of the shared partial, so including it is enough. The filter context is extracted into one helper used by the listing and the deck, so the two do not drift. Filtering uses the linked venue, so a show whose card displays a `venue_override` can sit under its linked venue's filter, as on the listing. The no-JavaScript bookmark returns to the full URL, so the filter survives with cookies off. The filter form sits above the deck, outside the player's box.

### 4b. Order: soonest show first
`discover` today calls `random.shuffle(cards)` on the whole deck, so an act whose next show is in April 2027 is as likely to come first as one playing tomorrow (the issue's screenshot). The shuffle is replaced by a sort on each card's `next_show` start time, using the shows left after the area filter, so the order follows the filter. `upcoming_performances` already orders shows by start time, so each card's first show is its next. To keep a little variety, cards whose next show is on the same New York calendar day are shuffled among themselves (group by day, shuffle each group, concatenate). Tests that fixed the shuffle by patching `random.shuffle` are changed to fix the within-day shuffle the same way. The deck is still never cached, as the same-day shuffle and bookmarks differ per visit. Sorting is in memory on cards already built, so the query count is unchanged. This supersedes the "random per visit" assumption of `add-band-discovery-swipe` (its open question 4 asked whether it should be soonest first). A cutoff, hiding acts whose next show is beyond a horizon, is not built: open question 9.

### 5. Genre
Acts have a `genres` array filled from MusicBrainz (`MusicAct`, `core/models.py`), but the listing has no genre filter and the data is sparse, so a genre filter would show a partial deck. The issue says "eventually"; it is left out, and no field or option is added. It is open question 4.

### 6. Screens
The Start control, the filter form on the deck and the "nothing matches the filters" state are new or changed screens, so the change is labelled `needs-design`. Option A was chosen: Start is a button over the top card's video thumbnail. The overlay sits on our own placeholder, which exists only before the player is loaded; the player itself is never overlaid.

### Mocking services in tests
No outside service is called, and tests never touch the network. Spotify, Apple Music and YouTube are `SpotifyArtistLink`, `AppleMusicArtistLink` and `YouTubeArtistLink` rows with the `*_PREVIEWS` switches set, as the existing deck tests do (`core/tests/discover_fixture.py`). The areas and venues come from `core/tests/geo_fixture.py`, as the listing's filter tests use. In browser tests (Playwright, `requirements-dev.txt`) every request to a service's embed address is routed to a stub page, so a test asserts which iframe was created and its `src` and `allow` (for example `autoplay=1`) and never whether sound actually plays, which no automated test can hear. Whether real browsers start the players is checked by hand on a phone and a desktop browser before the change is accepted, and the result recorded in the tasks.

## Risks / Trade-offs

- **Autoplay is best effort.** Browser policy, low-power modes and each service decide. Safari on iPhone is the strictest. The fallback, a ready player with its own play control, is what the deck does today, so a failure is not a regression.
- **Spotify and Apple Music may not autostart**, so for acts matched only there the deck may not feel automatic. YouTube-matched acts do.
- **A smaller deck.** Leaving out acts with no media, plus an area filter, can leave few or no cards; the empty states say why and link to the unfiltered deck.
- **Sound surprise.** Starting music on its own is expected here, but the Start control makes it the visitor's choice, and a passed card's sound always stops.
- **YouTube's terms.** Its Required Minimum Functionality rules (`PRODUCTION.md`) say nothing about overlays on autoplay specifically, but autoplay on an embedded player is documented as allowed; this is confirmed against the current terms before building.

## Open Questions

1. **The reference site.** How does nolajazzfest.stagehopper.app start its players (a first tap, muted, a service's own API)? It wasn't inspected. Nate should say, or the design round can copy what it does.
2. **Wording.** The code already treats right as add and left as skip. Should the right-hand label say "Add to my schedule" instead of "Add", and the site's "Saved shows" wording follow, or is "Add" enough? (The sketch shows the longer label, "Add to my schedule", only as an illustration.) And if the reporter still sees the reverse on their device, which device and browser?
3. **The first card.** Is a "Start" press before the first card plays acceptable, or is muted autoplay with an unmute tap preferred? Both are browser-legal; this proposal builds the Start press.
4. **Genre.** When there is genre data to filter on, should it be MusicBrainz's `genres` on acts or the venues' genres, and should the listing get it in the same change?
5. **Spotify's iFrame API.** May the deck load Spotify's iFrame API script to start its player? It is an extra script from Spotify; without it Spotify-only acts don't autostart.
6. **The remembered filter.** Should the deck share the listing's remembered filter (built here, so a bare `/discover` may redirect), or take only the URL's parameters?
7. **Acts left out by area.** Built here: a card lists only shows in the chosen area. Should it instead keep all of the act's shows and list the area's first?

8. **Photos.** The issue asked only to hide acts with no media; this change also removes card photos, since every card now has a player. Keep the photo beside the player instead?

9. **A horizon.** The deck is now ordered soonest first, so far-off shows come last but still appear for a visitor who swipes through the near ones. Should acts whose next show is more than some time away (for example 60 days) be left out of the deck altogether, and if so how far, or should it stay a pure ordering?

10. **The thumbnail.** The Start button sits over the top card's YouTube video thumbnail (the stored `video_id`'s image from YouTube's image address, loaded for the top card only). Is showing that thumbnail before a click allowed under YouTube's current developer policies, and does it count as loading from YouTube before the visitor acts, so that the visitor's address reaches YouTube on page view (the site otherwise stresses `youtube-nocookie.com`)? The terms and privacy check is recorded here before building, task 3.0. The thumbnail is for the top card only, never for the no-JavaScript list's other cards. If not, the button sits on a plain dark box. Acts with no `video_id`, or matched only on Apple Music or Spotify, show the plain box.

## Sketches

Option A, chosen by Nate and revised: the Start button is laid over the top card's video thumbnail rather than a black box. The other options were removed.

- [Option A: Start on the card](sketches/a.html). Thesis: the filter strip sits above the deck like the listing's, and the first card's player box shows the video's thumbnail with a Start button over it. Pressing Start removes both and loads the player. Risk: acts with no video thumbnail (Apple Music or Spotify only, or a YouTube channel match with no video) show a plain dark box; Start can be missed after a filter change reloads the page.
