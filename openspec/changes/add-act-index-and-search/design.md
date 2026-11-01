## Context

- Act pages: `core/views/act_page.py` sets `noindex` when the act has no upcoming show; `band.html` writes the meta tag. The sitemap (`core/sitemap.py`) lists only acts with an upcoming approved show.
- Search: `core/views/search.py` runs Postgres full-text search over events and static pages; the homepage hands `?s=` to it. No spec covers search yet (it came with nyc noise).
- The menu is `MenuItem` rows (an `OrderedModel`), edited in the admin.
- `import-curated-act-lists` adds `needs_review`; held acts already have no page.

## Goals / Non-Goals

**Goals:** every live act reachable by browsing and by search, on and off the site.

**Non-Goals:** resources (no model yet; decision 7 leaves room); fuzzy or misspelling-tolerant matching; filters on the index (by source, genre, state; the admin has the source filter); pagination; venue pages.

## Decisions

### 1. One index for bands and artists, at `/bands`
Visitors look for a name, not a kind, so both kinds share one A–Z list, each entry labelled. `/artists` redirects there rather than duplicating it.
*Alternative:* separate `/bands` and `/artists` indexes. Rejected: a visitor looking for "Anjimile" shouldn't have to know she's filed as an artist.

### 2. One query, grouped in Python
`Band` and `Artist` rows with `needs_review=False`, each annotated with its next upcoming approved show (`Min("performances__event__starttime")` filtered to approved events from the start of today), merged and sorted by name with a leading "The" dropped, grouped by first letter (`#` for anything else). At about 3,100 acts this renders in one page without pagination; the letter rail is the navigation.

### 3. The site's index-card look
The index is the band page's card: "Bands & artists" on the plum tab, a lavender letter rail (letters with no acts drawn quiet, not linked), and entries as ruled rows: the name bold and linked, then "Band · Providence, RI" in quiet grey, and the next show's date right-aligned in tabular figures. No design round: it's a list inside the established world (DESIGN.md), with the card, tab and ruled rows it already defines.

### 4. Names matched on their normalized form
Acts already store `name_key`, the name with case, accents, punctuation and a leading "The" removed (`core.artist_matching.normalize`); a search's words are normalized the same way and matched with `name_key__contains`, live acts only, ordered by name, 20 on the results page. Venues get the same treatment through `normalize(name)` on the fly (about 730 rows, or a stored key if it proves slow). Full-text search isn't used for names: a name is one phrase, and partial matches ("bell" finding Belly) are what visitors expect. Postgres's `unaccent` extension isn't installed (only `pg_trgm` is), and this needs no new extension.

### 7. Searchable kinds as a registry
`core/search_kinds.py` defines each kind once: its label ("Bands & artists", "Venues", "Shows"), a function that returns its matches for a query and a limit, and how each match renders (name, a quiet detail line, its link). The results page and the suggestions endpoint both walk the registry, so they never disagree, and resources join later as one more entry. Shows reuse the existing full-text event search for the results page; suggestions use upcoming approved events whose title or artists match, soonest first.

### 8. Suggestions: a small endpoint and an ARIA combobox
`/search/suggest?q=` returns `{"groups": [{"label", "items": [{"name", "detail", "url"}]}]}`, at most five per kind, empty under two characters, cached briefly per query. `search-suggest.js` turns the existing search input into a combobox (`role="combobox"`, `aria-expanded`, `aria-controls`, `aria-activedescendant` over a `role="listbox"` with grouped `role="option"`s), debounced 150ms, with arrow, Enter and Escape handling; the form still submits `?s=` when no option is active, and without the script it's the plain form it is today. The list is drawn in the site's style: card stock, a hairline border, group labels in quiet small caps, the active option on lavender.
*Alternative:* the browser's `<datalist>`, as the town box uses. Rejected: it can't group by kind, label items, or navigate to a link.

### 5. Indexable pages, a fuller sitemap
`noindex` is removed from `act_page` and `band.html` entirely. The sitemap lists `/bands` and every live act's page; held acts have no page, so they're excluded by the same `needs_review=False` filter.

### 6. The menu item by data migration
A data migration adds a "Bands & artists" `MenuItem` linking to `/bands` when none exists, so production gets it on deploy; editors can move or rename it in the admin.

## Risks / Trade-offs

- [Thin pages indexed: acts with only a name] → most live acts have MusicBrainz data, a bio or links; an act an editor thinks too thin can be held for review again in the admin.
- [3,100 entries on one page] → server-rendered text, no images; fine on phones. Pagination by letter is a later change if it grows tenfold.

## Migration Plan

Deploy with `import-curated-act-lists`; the menu item's migration runs on deploy. Rollback: revert; the menu item can stay or be deleted in the admin.
