Issue: [#133 Music Genres](https://github.com/natea/newenglandmusic/issues/133)

## Why

Venues and acts carry loose genre words with no fixed set: a venue's come from the sheet's `Venue_Genre_Search` column (`Funk`, `Jazz`, `ALL`), an act's from MusicBrainz tags (`indie rock`, `jangle pop`). Nothing can be filtered by them, and the words don't agree. Sooz (issue #133) supplied a curated list of 20 main genres with sub-genres, and asked that it become the official set and that visitors can filter by it, picking a main genre or a sub-genre.

## What Changes

- **The official genre list.** A `Genre` table holds the 20 main genres and their sub-genres exactly as listed in issue #133 (Alternative, Blues, Classical, Country, Decades, Easy Listening, Electronic/Dance, Folk, Freeform, Hip-Hop/Rap, Holiday, Inspirational, International, Jazz, Latin, Metal, New Age, Pop, Reggae, Rock, Urban and R&B). A sub-genre belongs to one main genre. Editors can add, rename and retire entries in the admin.
- **Venues and acts are tagged from the list.** `Venue` and `MusicAct` (bands and artists) each gain a many-to-many link to `Genre`, edited in the admin by picking from the list. Tagging with a sub-genre counts as tagging with its main genre too.
- **Existing words are matched, the rest flagged.** A command (`match_genres`, `--dry-run` first) maps each venue's sheet genre words and each act's MusicBrainz genre tags to the closest list entry, by a reviewed alias table and exact name match, never by guessing. Words that match nothing are listed on a review CSV and shown to editors in the admin, never dropped silently. An editor's tags are never overwritten.
- **The old words stay as evidence.** `Venue.genres` and `MusicAct.genres` keep their text (MusicBrainz's tags stay credited CC BY-NC-SA); the sheet sync keeps writing `Venue.genres` but never touches the new tags.
- **Filtering.** The calendar listing (`/` and the month pages) and the bands and artists index (`/bands`) get a genre picker offering main genres, with their sub-genres grouped beneath. Picking a main genre shows everything tagged with it or any of its sub-genres; picking a sub-genre shows only that one. A calendar show matches when its venue or any billed act carries the genre. The choice lives in the address (`?genre=jazz`, `?genre=big-band`), is not remembered in a cookie, and combines with the state and metro filter, and survives the remembered-filter redirect. The genre picker appears on the calendar and `/bands` only, not on the discover page. The picker offers only genres that some listed show or live act carries, and never retired genres; a retired sub-genre's tag stays but no longer counts when a main genre is picked.
- **Out of scope:** the ICS and calendar feeds, the weekly email, search, and the venue page's own genre line (venue pages are not built yet; see the design).

## Capabilities

### New Capabilities
- `genres`: the official two-level genre list, how venues and acts are tagged from it, and how old genre words are matched to it.
- `event-genre-filter`: filtering the calendar and the acts index by main genre or sub-genre.

### Modified Capabilities
- `event-geo-filter`: the remembered-filter redirect and the month links now keep a `genre` value (a genre alone is still not a geo filter and never sets the cookie). venue-records and artist-records are unchanged: they describe the old words, which stay.

## Impact

- **Models and migrations:** new `Genre`; `Venue.genre_tags` and `MusicAct.genre_tags` (M2M); the list loaded on every migrate (it creates missing entries only, matched by a stable `key` so renames never duplicate, and never deletes, unlike `GeoArea`).
- **Code:** `core/admin.py` (genre admin, pickers, unmatched-words panel), a `match_genres` command (a `RecordedCommand`), `core/views/index.py` (the remembered-filter redirect and month links keep `genre`), `core/geo_filters.py` and `core/views/act_index.py` (the filter), a genre picker partial beside `geo_filter_form.html`.
- **Data:** no external service; tags on events are derived from their venue and billed acts at query time, so no event is re-rendered.
