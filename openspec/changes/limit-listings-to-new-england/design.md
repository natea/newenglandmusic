Issue: [#58 Remove non-New England regions and states from the homepage search functionality](https://github.com/natea/newenglandmusic/issues/58)

## Context

- The homepage filters come from `GeoArea` rows synced from the sheet's geo-filters tab. `offered_areas(kind)` in `core/geo_filters.py` feeds the Region and State options in `core/views/index.py` and the metro groups; `parse_geo_filter` resolves URL and cookie slugs through it, so an area not offered is already dropped as unknown. The admin's sidebar filters (`core/admin.py`) use the same two functions.
- `Event.objects` hides unapproved events only. Listing (`index.py`), search, calendar feed, saved shows, act pages, discover, the search suggestions (`core/search_kinds.py`), and the sitemap all read it directly; so do the act next-show dates in `core/views/act_index.py` and `core/search_kinds.py`. `core/spotify_links.py` is also read directly, but by the artist-matching jobs, so it is left alone (decision 2); there is no shared place where "public" is decided beyond approval.
- Events link to a `Venue` (nullable) with a two-letter `state`. Pipeline commands (`fetch_events`, matching) must keep seeing every event.
- Issue #58 (sooz): remove the three regions and six states; phase 1 is "no events in the listings calendar or search for cities outside New England". Venues beyond New England are kept for later.

## Goals / Non-Goals

**Goals:** visitors see only New England events and search choices; one list to widen later; nothing deleted.

**Non-Goals:** removing venues or events from the database or admin; changing the sheet or `sync_venues_from_gsheets`; venue pages, venue search results and location lookups (see open questions).

## Decisions

### 1. One list of states, in code
A constant of the six state codes (`MA CT RI NH ME VT`) in `core/geo_filters.py`. Venue states are assumed stored uppercase, as the sheet sync writes them; a test with a lowercase venue state pins what happens. *Alternative:* a setting or a sheet column. Rejected for phase 1: the list changes rarely, and a code constant is visible in review and trivially tested.

### 2. A shared event filter, not a change to `Event.objects`
A helper returns `Q(venue__state__in=NEW_ENGLAND_STATES)`, passed as an extra filter alongside any geo filter's own Q (never replacing it), by each public view and by the sitemap. Act next-show dates (`act_index.py`, `search_kinds.py`) take the same condition on their `performances__event__venue__state` path, and acts whose only upcoming shows are outside New England show no date and drop out of the discover cards. The pipeline's readers are not touched: `upcoming_music_events()` in `core/spotify_links.py` feeds the Spotify, Apple Music, YouTube and Last.fm matching and the play-button re-baking, so filtering it would stop matching artists on out-of-region events, let their links expire after 30 days, and force rematching on rate-limited APIs in a later phase. Changing `Event.objects` itself would also hide events from `fetch_events` de-duplication, performer linking and the admin, which must see everything. Events with no venue are excluded, matching the existing rule that they belong to no area. *Scope of "hidden":* listing surfaces only. `/event/<id>` pages and their calendar links, and the saved-shows toggle, still work for an event opened by its id. *Why more than the calendar and search:* issue #58 asked for those two; the other public lists are included because otherwise the shows would reappear on band pages, feeds and the sitemap. That extension is an open question below. *Risk:* a new public view could forget the helper; the test for each listed surface covers today's ones.

### 3. Area options require all states inside New England, for the site only
`offered_areas(kind, new_england_only=False)` keeps its current behavior by default, which the admin's filters keep using. With `new_england_only=True` it keeps only areas whose `states` are all in the list. The site passes it: the index view's Region and State options, `metro_groups` and its state labels. States are compared lowercased on both sides, because `GeoArea.states` is stored lowercase while the constant is written uppercase, as `area_q` already does; a test with lowercase area states guards that every New England area survives. The constant is `NEW_ENGLAND_STATES` in `core/geo_filters.py`, which the widening test patches. Tri-State is assumed to include a state outside New England (New York or New Jersey), which is all the rule needs to drop it; the test fixture has no Tri-State rows, so the first real run checks the sheet.

### 4. Stale slugs follow the site's parser
`parse_geo_filter(querydict, new_england_only=False)` passes the flag to `offered_areas`. The site's callers (`geo_filter_for_request`, so the homepage, month archives and cookie, and the calendar feed) pass `True`, so old links and cookies to removed areas are dropped as unknown and the cookie path clears a cookie that resolves to nothing. The admin calls it without the flag, so it still resolves every area. Tests pin both. Old calendar subscriptions naming a removed area become the unfiltered New England feed.

## Risks / Trade-offs

- [A venue's state is blank or wrong in the sheet, so a New England show disappears] → blank-state venues are hidden under this rule; the verification step counts upcoming events dropped and lists blank-state venues for an editor.
- [Border venues in New York with New England audiences vanish] → intended for phase 1; the list is one line to widen.
- [Sitemap and search suggestions diverge from the listing] → all use the same helper.

## Migration Plan

No schema or data change. Deploy, then spot-check `/`, search and the filter menus. Rollback is reverting the commit.

## Test mocking

Tests use Django `TestCase` with venues and events created directly and the trimmed geo areas from `core/tests/geo_fixture.py`. Google Sheets (`gog`), venue websites, Anthropic, ticketing APIs, Spotify, Apple Music, YouTube, Last.fm, MusicBrainz, OpenStreetMap and Google Places are not called by this change; any test touching a command that would is mocked or replayed as the existing tests do, with the network blocked.

## Open Questions

- **Venue pages, venue search results and the location form's town and ZIP lookup:** the issue says events only. Should venues outside New England also leave venue search and the location form now? Left as is until answered.
- **Events with no venue:** hidden too, as they belong to no area; sooz only said cities outside New England. Hide them, or show them?
- **Blank-state venues:** hidden under this design. Is that acceptable, or should an editor fix their state first?
- **Duplicate of #6:** the thread notes a possible overlap; Nate should compare before building.
- **Wider than the issue:** besides the calendar and search, feeds, saved shows, band pages, discover and the sitemap also hide out-of-region events. Keep that, or limit phase 1 to the calendar and search?
- **Direct links and venue-name suggestions:** event pages by id still open, and a venue-name search suggestion for an out-of-region venue leads to a search with no results. Acceptable for phase 1?
- **Artist matching:** left unfiltered so Spotify, Apple Music and YouTube matching is unchanged. Should it narrow to New England in phase 2?
