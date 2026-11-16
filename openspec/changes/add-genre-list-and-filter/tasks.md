Issue: [#133 Music Genres](https://github.com/natea/newenglandmusic/issues/133)

## 1. The genre list

- [ ] 1.1 Add the `Genre` model (key, name, slug, parent, is_retired, sort_order; two levels only) and its migration; verified by a test for "Two levels only" (a sub-genre cannot take a sub-genre as parent)
- [ ] 1.2 Add `core/genres.py` with the 20 main genres and sub-genres exactly as in issue #133, and a sync keyed on each entry's stable `key` that creates missing entries on every migrate without overriding editors' changes; verified by tests for "The list is loaded", "Migrating again changes nothing", "A renamed genre is not recreated" (rename, migrate, assert no new row) and a test that all slugs and keys are unique
- [ ] 1.3 Register `Genre` in the admin (main genre shown, retire, rename, add); verified by a test for "A genre with a main genre"

## 2. Tags on venues and acts

- [ ] 2.1 Add `Venue.genre_tags` and `MusicAct.genre_tags` (M2M, excluding retired from the picker) with a migration; verified by tests for "Tagging a venue" and "Retired genres are not offered"
- [ ] 2.2 Show the pickers in the venue, band and artist admin, with the unmatched old words beside them; verified by an admin test for the unmatched words panel
- [ ] 2.3 Confirm the sheet sync and MusicBrainz enrichment leave tags alone; verified by tests for "Sheet sync" and "Enrichment", using the existing `gog` mock and MusicBrainz fixture

## 3. Matching existing words

- [ ] 3.1 Write `core/genre_aliases.py` and the matching function (exact name, alias, else unmatched; `ALL` ignored); verified by tests (with an injected alias table) for "Exact and alias matches", "A word that fits nothing" "ALL adds nothing" and "Hand-tagged record"
- [ ] 3.2 Add the `match_genres` command as a `RecordedCommand` with `--dry-run` and `--csv`, tagging only untagged records; verified by tests for "An editor's tags are kept", "Dry run", "Review file" and "Original words remain"
- [ ] 3.3 Note the command in `AGENTS.md` and `PRODUCTION.md`; verified by reading both

## 4. Filtering

- [ ] 4.1 Resolve `genre=<slug>` to a genre and its non-retired sub-genres and ignore unknown or retired values; verified by tests for "Unknown genre", "Retired genre", "Retired sub-genre" and "Main genre"/"Sub-genre"
- [ ] 4.2 Filter the calendar by venue tags or billed acts' tags (separate artist and band subqueries) (once per show, held acts excluded), combined with the geo filter and carried in month links and the mini month grid's day links (`geo_query` is built today only when a geo filter is set, so build it for a genre-only filter too); verified by tests for "Matching by billed act", "Listed once", "An act held for review", "Combined with state", "Month links", "Shared link" and "Not remembered", plus query-count assertions on the unfiltered and the filtered page, and a test that `no_matching_events` is true for a genre-only filter
- [ ] 4.3 Filter the acts index by the same set; verified by tests for "Acts by main genre" (including one tagged artist and one tagged band) and "Inactive and held acts"
- [ ] 4.4 Add the genre picker (grouped, used genres only, no-JS form) to both pages, and the empty message (shown for a genre-only filter too, its link keeping the geo filter); after design sketches, match them; the `/bands` picker is its own small form, since that page has no geo filter form today; verified by tests for "Picker contents", "Main genre offered for a used sub-genre", "Unused genres are not offered" and "Empty result", and a browser test that the picker submits
- [ ] 4.5 Keep `genre` through the remembered-filter redirect and exempt the hidden genre field from the form script's and the server's "clear" rule; verified by tests for "Clearing the state keeps the genre", "Show all clears both" "Not offered on discover" and "Genre kept through the redirect" (the cookie is set before the request in the redirect scenarios), and that every existing `event-geo-filter` test still passes; discover's redirect and form stay unchanged (the geo helper itself isn't modified; the genre is carried only in the index view); change `artists_index` (`core/views/act_index.py`) to carry the query string, verified by "Old address kept" for `/artists?genre=`; the "Clearing the state keeps the genre" test posts the real form fields (empty geo fields beside the hidden `genre`)
- [ ] 4.6 Check the example genre names in the specs against issue #133 and fix any that differ
- [ ] 4.7 Run `venv/bin/python manage.py test` with the network blocked; verified by a green run
