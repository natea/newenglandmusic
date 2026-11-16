Issue: [#133 Music Genres](https://github.com/natea/newenglandmusic/issues/133)

## Context

- **Today's genre fields:** `Venue.genres` (an array of words from the sheet's semicolon-separated `Venue_Genre_Search`, sometimes `ALL`) and `MusicAct.genres` (up to 10 MusicBrainz tags, CC BY-NC-SA, credited on the act page and in the admin). Both are plain text arrays; `Venue.genre_notes` holds free notes. Neither is used to filter anything.
- **Writers of the old words:** `sync_venues_from_gsheets` overwrites `Venue.genres` (run by hand); `enrich_artists_from_musicbrainz` rewrites `MusicAct.genres`. Editors cannot rely on either to keep tags, so tags need their own field.
- **Listing:** `index` and `past_month_archive` go through `_get_events_page_for_month`, which builds `Event.objects.select_related("venue").filter(geo_filter.q(prefix="venue__"), new_england_q(...))` and renders the stored HTML of each event. A filter on the query set changes nothing stored, so no `resave_all_events`.
- **Billing:** `EventPerformer` links an event to its `Artist`/`Band` in billing order. `live_acts()` in `core/views/act_index.py` lists acts that aren't `needs_review` or `is_inactive`.
- **Geo filter:** `geo_filter_for_request` reads `state`, `metro`, `town` from the address or a cookie and renders `geo_filter_form.html` as a GET form. Month links carry `geo_query`.
- **Areas as precedent:** `GeoArea` is declared in code (`core/geo_areas.py`) and loaded by every migrate (`core/geo_area_sync.py`).
- **Outside services:** none are needed.

## Goals / Non-Goals

**Goals:**
- One official two-level list, as supplied in issue #133, that editors can maintain.
- Tags on venues and acts that survive the sheet sync and MusicBrainz enrichment.
- A genre filter on the calendar and the acts index, main genre or sub-genre.

**Non-Goals:**
- Tagging individual events: an event's genres are derived from its venue and acts.
- Filtering the calendar feeds, the weekly email, search or the discover swipe.
- Automatic or AI genre assignment beyond exact and reviewed-alias matching.
- Showing genres on the act page or in listings (the act page keeps showing the credited MusicBrainz words).

## Decisions

**A `Genre` table with a self-link, not a constant list.** Fields: `key` (unique, set from the list in code and never changed, so renames don't break the sync), `name`, `slug` (unique), `parent` (null for a main genre), `is_retired`, `sort_order`. Editors need to add and retire entries without a deploy, and the two levels are fixed (a parent has no parent; enforced in `clean`). Alternatives: a Python constant and a text array of names (no integrity, renames orphan tags); full tree library (more than two levels isn't needed).

**The list lives in `core/genres.py` and is loaded by every migrate**, like `GeoArea`. The sync matches entries by `key` (for example `jazz` and `jazz/big-band`), not by name, creates those missing and never renames, reparents or un-retires one an editor changed, so editors' edits win and a renamed "Big Band" is not recreated. An entry an editor added by hand has no key and is never touched; if its name later equals a list entry, the list entry is still created (the editor can retire one). Slugs come from the name; a clash adds the main genre's slug (checked against the list when the data is written, with a test).

**M2M tags `Venue.genre_tags` and `MusicAct.genre_tags`, beside the old arrays.** The old arrays are evidence the sync and MusicBrainz keep rewriting (and MusicBrainz's must stay credited); the tags are editor-owned. `Venue.save()` re-renders each event's stored HTML, so tagging goes through the admin's normal save only because that already happens, and `match_genres` writes tags through the M2M relation, which does not call `Venue.save()`. Alternative: replace the arrays: rejected because the next sheet sync or enrichment would repopulate them.

**Matching (`match_genres`).** For each distinct word, normalise (lowercase, drop punctuation and spacing) and look up: exact name of exactly one list entry, else a repo alias table (`core/genre_aliases.py`, entries such as "hip hop" → "Hip Hop" are only illustrative; the real table is for Sooz to review), else unmatched. An ambiguous exact name (same name under two mains, if the list ever has one) is unmatched. It only touches a venue or act that has no tags yet, so an editor's tags, including deliberately empty ones after an edit, are never overwritten; to retry, an editor clears the tags first. A `RecordedCommand`; `--dry-run`, `--csv` for the review file with counts of venues and acts per word. Unmatched words per record are computed, not stored: the admin panel and the CSV re-run the matcher over the record's old words and list those that match nothing, whether or not the record's tags came from the command. A hand-tagged record therefore still lists its unmatched words, and a word is not shown as unmatched when it matches a list entry even if the editor didn't tag it. Tests inject their own alias table rather than reading `core/genre_aliases.py`.

**Filter semantics.** `genre=<slug>` resolves to a set of genre ids: the genre plus its non-retired children when it is a main genre, else just itself. A retired slug is ignored, and the picker never offers retired genres, so a venue that keeps a retired sub-genre tag no longer matches through its main genre. An event matches when `venue__genre_tags` is in the set, or an `EventPerformer` act's tags are. Because `EventPerformer` points at `Artist` or `Band` (and `MusicAct` is their shared base), the act side is a subquery on the performer table filtered to acts with `needs_review=False`, then `Event.pk IN (...)` to avoid duplicate rows from joins. `EventPerformer` has separate `artist` and `band` foreign keys, so the act side is two subqueries (`performances__artist__genre_tags` and `performances__band__genre_tags`) joined with OR. The acts index applies the same set to both models' `live_acts()` queries. The calendar excludes only `needs_review` acts, while the index also excludes `is_inactive`; this asymmetry is deliberate and tested.

**Address, not cookie.** `genre` is a plain GET value, not part of `GeoFilter` or its cookie: a remembered genre would silently empty the calendar, and a shareable link is the point. It is carried by month links and the state/metro form (as a hidden field) alongside `geo_query`. An unknown or retired slug is ignored. `/artists` redirects to `/bands`, but today `artists_index` drops the query string, so it is changed to carry it (as `without_trailing_slash` does) and `genre` survives the redirect.

**Genre and the remembered geo filter.** `geo_filter_for_request` redirects an address with no `state`, `metro`, `town` or `clear` to the cookie's geo filter. That redirect (in `index` and the month pages) SHALL carry `genre` along, so `?genre=jazz` with a remembered Vermont filter goes to `?state=vermont&genre=jazz`; the cookie's geo filter shows in the address, and the genre is never lost. A genre alone does not count as a geo parameter and never sets the cookie. The hidden `genre` field in the state/metro form is exempt from the form script's "some field has a value" test and from the server's "all geo fields empty means clear" rule: both look at geo fields only, so with a genre picked, choosing state "All" still clears the remembered filter and keeps the genre. The existing "show all" link (`?clear=1`) clears both the geo filter and the genre. The empty-result message appears for a genre-only filter too, and its link drops the genre but keeps the geo filter. The view's `no_matching_events` flag and `geo_query` (today derived from the geo filter alone) are also derived from a picked genre, so a genre-only filter shows the message and keeps its month links. The calendar's `calendar_links` subscribe box is unchanged and ignores the genre.

**Where the picker renders.** The calendar pages and `/bands` only. `geo_filter_form.html` is shared with the discover page, so the hidden genre field is an optional include parameter that discover does not pass; discover ignores `genre` and its own redirect to the remembered filter doesn't carry it. The calendar's subscribe box still offers feeds that ignore the genre (feeds are out of scope).

**Why the acts index is included.** The thread asked for the filter on the calendar and venue pages and answered "official set plus filter"; the index reuses the same set and picker cheaply and is where tagged acts are found. The earlier act-index design listed a genre filter as a non-goal at the time, not a prohibition. It is easy to drop; say so if unwanted.

**Old words kept, not replaced.** The bridge's summary said the list would replace the loose words. This design deliberately keeps them (see the M2M decision), since the sheet sync and MusicBrainz would repopulate them and MusicBrainz's tags must stay credited.

**Picker lists only used genres** (the proposal's own choice, neither Sooz's nor the owner's, so it is also an open question below; so the picker isn't padded with empty groups while few records are tagged). A main genre appears as a group when it or any of its sub-genres is used, with "All <main>" first; only used sub-genres are listed under it. Options come from genres on tagged venues or acts with a listed upcoming show (calendar) or live acts (index), grouped under the main genre as `<optgroup>`; the main genre itself is the first option of its group, labelled "All Jazz". A plain GET form, with the same small script as the geo filter that submits on change.

**Alternatives for the picker:** main genres first, then sub-genres once one is chosen. The thread asked for both to be pickable at once, so the grouped single select is used. Whether it should become a two-step control is a design-round matter (see Sketches).

## Risks / Trade-offs

- [Example list entries in the spec (Tribal, Mariachi, Celtic under International, Indie Rock, Folk Rock under Folk, Bluegrass) were written without checking issue #133] → the implementer must check each against the issue's text and correct the spec.
- [Many existing words won't match, leaving most records untagged and the filter thin] → the review CSV and admin panel make the gap visible; aliases are added over time; no guessing.
- [A filter that matches by acts as well as venues surprises: a jazz night at a rock club only under the act's tags] → intended; the venue-only variant is an open question.
- [Venue tags are coarse (a venue's genres aren't every show's)] → stated; shows inherit them. Act tags make precise matches where acts are linked.
- [The `Decades` and `Freeform` groups aren't genres (Oldies, Rainy Day Mix, Women)] → kept as supplied, since the list is the owner's; an editor can retire any.
- [Query cost] → the picker's options need queries on every calendar and `/bands` load, and the act subquery runs when a genre is picked; test with a query-count assertion on both an unfiltered and a filtered page.

## Migration Plan

1. Migration adds `Genre` and the two M2M fields; the list loads on migrate.
2. Deploy, then run `match_genres --dry-run`, read the CSV, add aliases, then run it for real. It's by hand first; whether it joins the weekly job is an open question.
3. Rollback: the picker and filter are the only visible parts; reverting the code leaves the tables inert.

## Sketches

The picker's look on the calendar and the acts index (one grouped select, or main genres first with sub-genres after) needs a design round, hence the `needs-design` label.

Three options for the genre picker, shown on the calendar with Jazz chosen:

- [Option A: One grouped select](sketches/a.html). Thesis: the genre picker is one more select in the existing filter strip, with each main genre as a group whose first entry is "All Jazz" and its sub-genres beneath; it matches the geo filter's pattern and costs the least space and code. Risk: a long grouped list is hard to scan in a native select, especially on a phone, and the two levels sit in one flat menu, so the choice is easy to misread.
- [Option B: Main genres, then sub-genres](sketches/b.html). Thesis: a row of main-genre chips sits under the filter strip; choosing one opens a second row of its sub-genres with "All Jazz" first, so both levels are visible without menus. Risk: two extra rows push the shows down on the calendar and `/bands`, wrap badly on narrow screens, and depart from the strip's select style.
- [Option C: Genre rail with counts](sketches/c.html). Thesis: a left rail lists main genres with counts and expands the chosen one to show its sub-genres, so a visitor sees what the filter will find before clicking. Risk: counts need extra queries per page, the rail costs width on a dense, text-first page, and it must collapse above the listing on narrow screens.

## Testing and mocking

No outside service is called. Tests use Django `TestCase` with small hand-made venues, acts and events. `match_genres` tests build `Venue.genres` and `MusicAct.genres` directly; they do not call MusicBrainz or the sheet. The sheet sync and enrichment tests that assert tags are untouched reuse the existing `gog` mock and `core/tests/musicbrainz_fixture.py`. The suite runs with the network blocked.

## Open Questions

- **Picker lists only used genres?** Sooz asked to pick from main genres and sub-genres; with few records tagged the picker will be short. Listing the whole list is the alternative.
- **Weekly `match_genres`?** `match_genres` skips tagged records, so once enrichment refreshes MusicBrainz tags, new words are never matched for tagged acts; an editor clears tags to retry.
- **Venue-only or venue and act matching?** The design matches through both; if editors find act tags too noisy, the calendar could use the venue's tags only. The spec would change.
- **Does `match_genres` join the weekly job?** Not by default, since an editor's review comes first.
- **Aliases:** which words map where (for example "r&b", "hip hop", "indie rock") is for Sooz to review from the first dry run's CSV.
- **Venue pages:** `add-venue-pages` isn't built yet; its genre line and any filter there come later, after this change.
- **The `ALL` venues:** untagged for now; whether they should count as every genre is undecided.
- **Venue filtering already built?** A later comment on the issue shows a screenshot of a venue filter, addressed to Sooz, that nobody has tied to this change. It picks none of the three sketches and asks for no change, so the proposal is unchanged. Whether that venue filter should be reconciled with the genre picker here, or whether the sketch choice (a, b or c) still stands, is undecided; the next round should settle it.
