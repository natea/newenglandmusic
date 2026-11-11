# bandcamp-embed Specification

## Purpose

Lets visitors hear an act that has a Bandcamp page in Bandcamp's own embedded player, on event listings and on artist and band pages. A weekly command reads the player's album or track ID from the act's own Bandcamp page once and keeps it, so no page view ever asks Bandcamp for anything.

## ADDED Requirements

### Requirement: A record keeps its Bandcamp player
An artist or band SHALL keep the kind of its Bandcamp player (`album` or `track`), the numeric ID, the time it was last looked up, a status (`found`, `no_playable` (no playable release), `blocked`, `gone`, `unreadable`, `failed`, or blank for never looked up), and the Bandcamp URL the player was read from.  The player's address SHALL be built from the kind and ID alone, as `https://bandcamp.com/EmbeddedPlayer/album=<id>/…` or `…/track=<id>/…`, and only when the ID is all digits.

#### Scenario: Player address from an album ID
- **WHEN** a band's player is kind `album`, ID `1234567890`
- **THEN** its player address is on `bandcamp.com/EmbeddedPlayer/album=1234567890/`

#### Scenario: The URL a player was read from
- **WHEN** the lookup finds a player for a band
- **THEN** the band also keeps the Bandcamp URL it was read from, and the player stops being usable if the band's URL later changes (an editor's player is exempt)

#### Scenario: An ID that is not a number
- **WHEN** an editor saves a player ID of `12ab"><script>`
- **THEN** the admin rejects it and nothing is saved

### Requirement: Only a usable player is shown
A player SHALL be *usable* when its kind and ID are set and either an editor set it (marked "editor" in `field_sources`), or its status is `found` and the URL it was read from equals the act's current Bandcamp URL. Every place the site shows a player SHALL require a usable one.

#### Scenario: Stale player is not usable
- **WHEN** a band's found player was read from one Bandcamp URL and an editor has since changed the band's URL
- **THEN** the player is not usable and no button or section shows it

### Requirement: An editor's player is never overwritten
An editor SHALL be able to set or clear the kind and ID in the admin. A value an editor set SHALL be marked "editor" in `field_sources`, and the lookup SHALL NOT overwrite or clear it. Saving an editor's player SHALL leave it usable, whatever the status.

#### Scenario: An editor's player is shown
- **WHEN** an admin sets a band's player and the band's status is blank
- **THEN** the band's player is usable and its events and page show it

#### Scenario: An editor's player stays
- **WHEN** the lookup runs for a band whose player an editor set
- **THEN** the band's kind, ID and status are unchanged and no request is made for it

### Requirement: The ID is read once from the act's own page
`find_bandcamp_embeds` SHALL, for an act with a Bandcamp URL, fetch that one page and read the ID of a playable release from it. When the page redirects to a release, it SHALL take the ID from the release's structured data (the `albumRelease` `item_id` in its JSON-LD, or for a track the page's properties). When the page shows a discography grid, it SHALL take the first music tile's `data-item-id` (`album-<id>` or `track-<id>`).

#### Scenario: Redirect to a featured album
- **WHEN** an act's page redirects to an album whose JSON-LD gives `item_id` 111
- **THEN** the act is saved as kind `album`, ID 111, status `found`

#### Scenario: Redirect to a track
- **WHEN** an act's page redirects to a track whose page properties give track ID 222
- **THEN** the act is saved as kind `track`, ID 222, status `found`

#### Scenario: Discography grid
- **WHEN** an act's page is a grid whose first music tile is `album-333`
- **THEN** the act is saved as kind `album`, ID 333

### Requirement: Merchandise is skipped
The command SHALL skip merchandise tiles, and when the front page has no music tile it SHALL try the same page's `/music` path once.

#### Scenario: Merchandise first
- **WHEN** an act's front page is a grid of merchandise only, and its `/music` page's first tile is `track-444`
- **THEN** the act is saved as kind `track`, ID 444

### Requirement: A release that can't be played is skipped
Before saving an ID the command SHALL check that Bandcamp's player for it is available, by requesting the player's address once. When the player says the release is not available, the command SHALL go on to the next music release in the page, trying at most three in all. When none plays, the act SHALL be saved with status `no_playable`, no ID, and the time checked.

#### Scenario: Physical-only first release
- **WHEN** an act's first release (`album-555`) has no playable player and its second (`album-556`) does
- **THEN** the act is saved with ID 556

#### Scenario: Nothing playable
- **WHEN** the first three releases of an act all have an unavailable player
- **THEN** the act is saved with status `no_playable` and no ID, and nothing more is requested for it

### Requirement: Polite requests
The command SHALL obey robots.txt (asked for once per host a run), send the user agent `venue-db-event-check/1.0`, wait about two seconds between requests, use no proxy, run no JavaScript, and follow redirects only within bandcamp.com and its subdomains.

#### Scenario: Robots forbids it
- **WHEN** Bandcamp's robots.txt disallows the act's page
- **THEN** no request is made for the page, and the act's status is `blocked`

#### Scenario: A redirect off Bandcamp
- **WHEN** an act's page redirects to another site
- **THEN** that redirect is not followed, and the act's status is `failed`

### Requirement: Failures are recorded, and only the ID is kept
For an act with no found player, a request answered 403, 406 or 429 SHALL set status `blocked`; 404 or 410, `gone`; a page with no release, `unreadable`; a timeout or other error, `failed`. The command SHALL store nothing from a page but the kind and ID, and SHALL stop the run when Bandcamp blocks three acts in a row.

#### Scenario: A deleted page
- **WHEN** an act's Bandcamp page answers 404
- **THEN** the act's status is `gone`, and the act's address is left as it is

### Requirement: A failed refresh never hides a found player
For an act that already has a found player, every non-success outcome of a refresh (403, 406, 429, 404, 410, 500, a timeout, a robots.txt refusal or an unreadable page) SHALL leave the ID, kind, status `found` and the URL it was read from as they are, update only the time checked, and be reported as a problem of the run.

#### Scenario: A failed refresh of a found player
- **WHEN** a band with a found player is refreshed and its page answers 404, and another's answers 429
- **THEN** both keep their ID and status `found`, their time checked is updated, and each is reported as a problem

#### Scenario: Blocked repeatedly
- **WHEN** three acts in a row answer 429
- **THEN** the run stops, the rest are left for the next run, and the run is recorded with a problem

#### Scenario: Nothing else is kept
- **WHEN** a page is read and a player ID found
- **THEN** only the kind, ID, status and time are saved, with no title, artwork or text

### Requirement: Looked up once, refreshed rarely, never on a page view
The command SHALL look up an act with a Bandcamp URL that has never been looked up; one with status `found` again after 365 days; one with `no_playable`, `unreadable`, `failed` or `blocked` after 90 days; and one whose Bandcamp URL changed since the last lookup at its next run. It SHALL skip an act without a Bandcamp URL. A look-up that fails SHALL keep an earlier `found` ID (see the failures requirement). No page view, event save or admin save SHALL request anything from Bandcamp.

#### Scenario: Never looked up
- **WHEN** a band has a Bandcamp URL and has never been looked up
- **THEN** the run looks it up

#### Scenario: Recently looked up
- **WHEN** a band was found 30 days ago
- **THEN** the run makes no request for it

#### Scenario: Old no-playable result
- **WHEN** a band was `no_playable` 100 days ago
- **THEN** the run looks it up again

#### Scenario: Address changed
- **WHEN** an editor changes a band's Bandcamp URL after it was found
- **THEN** the next run looks it up again, and until then its old ID is not shown

#### Scenario: A failed refresh keeps the ID
- **WHEN** a band with a found ID is refreshed and the page answers 500
- **THEN** its ID stays, its status is `found`, and it is tried again at the next due time

#### Scenario: A page view
- **WHEN** a visitor opens the homepage or a band page
- **THEN** the server makes no request to Bandcamp

### Requirement: Limits and a dry run
`--limit` SHALL cap the acts looked up in a run, which SHALL be capped at 100 when `--limit` is not given, as the Spotify and YouTube commands cap themselves, so a run stays short (each act may cost up to five requests about two seconds apart); `--refresh` SHALL look up every act with a Bandcamp URL, and `--dry-run` SHALL print what would be saved and save nothing.

#### Scenario: Dry run
- **WHEN** the command runs with `--dry-run`
- **THEN** it prints each act's would-be result and saves nothing

#### Scenario: Limit
- **WHEN** 10 acts are due and the command runs with `--limit 3`
- **THEN** 3 acts are looked up

#### Scenario: Default cap
- **WHEN** 150 acts are due and the command runs without `--limit`
- **THEN** 100 acts are looked up and the rest are left for the next run

#### Scenario: Refresh
- **WHEN** the command runs with `--refresh` and a band was found 10 days ago
- **THEN** the band is looked up again

### Requirement: A Bandcamp button on event listings
An event listing SHALL show a Bandcamp button in the row of play buttons, after the Spotify, Apple Music and YouTube buttons of the same artist, for each performer (artist or band) linked to the event, in billing order, that has a usable player. The button SHALL be a plain link to the act's Bandcamp page, named "Listen to <name> on Bandcamp". With JavaScript, pressing it SHALL open Bandcamp's player below the row, and nothing SHALL load from Bandcamp before that.

#### Scenario: Event row with a player
- **WHEN** an event lists a band with a found player and a Spotify match
- **THEN** its row shows the Spotify button, then the Bandcamp button

#### Scenario: Only Bandcamp
- **WHEN** an event lists a band with a usable player and no other match
- **THEN** its row shows only the Bandcamp button

#### Scenario: No other service configured
- **WHEN** Spotify, Apple Music and YouTube previews are all switched off and an event lists a band with a usable player
- **THEN** the event's row still shows the Bandcamp button, and `artist_preview.js` opens its player on a click

#### Scenario: Nothing loads until pressed
- **WHEN** the homepage lists events with Bandcamp buttons
- **THEN** the page contains no Bandcamp iframe, and none is requested until a button is pressed

#### Scenario: Pressing the event button
- **WHEN** a visitor with JavaScript presses a Bandcamp button
- **THEN** Bandcamp's player for that act opens below the row, and any other open player closes

#### Scenario: Event button without JavaScript
- **WHEN** a visitor without JavaScript clicks the button
- **THEN** the act's Bandcamp page opens in a new tab

### Requirement: Which acts get a button
An act that is held for review or has no usable player (including one whose Bandcamp URL changed since its player was found, unless an editor set it) SHALL get no button. The button SHALL be in the event's stored HTML, as the other buttons are. The button SHALL NOT depend on any other player service being switched on.

#### Scenario: Act with no usable player
- **WHEN** an event lists a band whose status is `no_playable`, or one held for review
- **THEN** its row has no Bandcamp button

### Requirement: Events are re-rendered when a button changes
The events of an act SHALL be re-rendered whenever what decides its button changes: the lookup finding or changing a player, an editor setting or clearing a player or changing the Bandcamp URL in the admin, the act's held-for-review mark being toggled (including by marking it ready or by the act-list import), the act's performer links being rebuilt, and the act being deleted.

#### Scenario: Events re-rendered
- **WHEN** the lookup finds a player for a band with upcoming events
- **THEN** those events are re-rendered with the button

#### Scenario: Events re-rendered after an editor's change
- **WHEN** an admin sets, clears or changes a band's player, or changes its Bandcamp URL, or marks it ready after review, or the band is deleted
- **THEN** the band's upcoming events are re-rendered, so the listing shows the button only while the band has a usable player

#### Scenario: Events re-rendered after performer links change
- **WHEN** an event's performer links are rebuilt to include a band with a usable player
- **THEN** the event is re-rendered with the button

### Requirement: Player order for the discovery deck
Wherever the site offers an act's players in a fixed order, it SHALL put Bandcamp last: YouTube, Apple Music, Spotify, Bandcamp for the discovery deck; and Spotify, Apple Music, YouTube, Bandcamp for the event row. A single function in `core/artist_previews.py` SHALL give each act's players in that order for each screen, so a screen that has no Bandcamp player skips it.

#### Scenario: Deck order
- **WHEN** an act has a Bandcamp player and a Spotify player
- **THEN** the deck's order for the act lists Spotify before Bandcamp

#### Scenario: Full order
- **WHEN** an act has YouTube, Apple Music, Spotify and Bandcamp players
- **THEN** the deck's order is YouTube, Apple Music, Spotify, Bandcamp, and the event row's order is Spotify, Apple Music, YouTube, Bandcamp

#### Scenario: Only Bandcamp in the deck
- **WHEN** an act has only a Bandcamp player
- **THEN** the deck's order for the act is the Bandcamp player alone

### Requirement: Staff manage players in the admin
The admin's artist and band forms SHALL show a "Bandcamp player" fieldset: the kind and ID (editable), the status, the time and the URL the player was read from (read-only), and a list filter on the status. Saving an edited kind or ID SHALL mark it "editor", which makes the player usable. Clearing both SHALL remove the editor's mark so the lookup may fill it again.

#### Scenario: Editor sets an ID
- **WHEN** an admin sets a band's kind to `album` and ID to 777
- **THEN** the band's player is that album and `field_sources` marks it "editor"

#### Scenario: Clearing
- **WHEN** an admin clears an editor's player
- **THEN** its mark is removed, and the next run looks the band up

#### Scenario: Filter
- **WHEN** an admin filters the band list to "no playable release"
- **THEN** only bands with that status are listed
