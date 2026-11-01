## Context

- Act pages: `core/views/act_page.py` sets `noindex` when the act has no upcoming show; `band.html` writes the meta tag. The sitemap (`core/sitemap.py`) lists only acts with an upcoming approved show.
- Search: `core/views/search.py` runs Postgres full-text search over events and static pages; the homepage hands `?s=` to it. No spec covers search yet (it came with nyc noise).
- The menu is `MenuItem` rows (an `OrderedModel`), edited in the admin.
- `import-curated-act-lists` adds `needs_review`; held acts already have no page.

## Goals / Non-Goals

**Goals:** every live act reachable by browsing and by search, on and off the site.

**Non-Goals:** resources (no model yet; decision 5 leaves room); fuzzy or misspelling-tolerant matching; filters on the index (by source, genre, state; the admin has the source filter); pagination; venue pages.

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

### 5. Searchable kinds as a registry
`core/search_kinds.py` defines each kind once: its label ("Bands & artists", "Venues", "Shows"), a function that returns its matches for a query and a limit, and how each match renders (name, a quiet detail line, its link). The results page and the suggestions endpoint both walk the registry, so they never disagree, and resources join later as one more entry. Shows reuse the existing full-text event search for the results page; suggestions use upcoming approved events whose title or artists match, soonest first.

### 6. Suggestions: a small endpoint, and GOV.UK's accessible-autocomplete for the box
`/search/suggest?q=` returns `{"items": [{"kind", "group", "name", "detail", "url"}]}`, `kind` being "band", "artist", "venue" or "show", at most five per kind in group order, empty under two characters, cached briefly per query.
The box is [accessible-autocomplete](https://github.com/alphagov/accessible-autocomplete) 3.0.2 (MIT, released 2026-09-24), the GOV.UK Design System's combobox, which handles the keyboard (arrows, Enter, Escape), ARIA roles and what screen readers announce, and is tested with them. Its two files (`accessible-autocomplete.min.js` and `.min.css`) are kept in `core/static/core/vendor/accessible-autocomplete/3.0.2/`, not loaded from a CDN, so the site makes no third-party request and the version is pinned. `core/static/core/js/search-suggest.js` mounts it on the search box with:
- `source`: debounced (150ms) fetch of `/search/suggest`, nothing under two characters (`minLength: 2`);
- `templates.suggestion`: each row as its kind tag ("Band", "Artist", "Venue", "Show", in the pill style) then the name in bold and the quiet detail (town; or date and venue for a show), with the group's label shown above the first row of each group;
- `templates.inputValue`: the name, so choosing fills the box as expected;
- `onConfirm`: going straight to the chosen item's `url`; with nothing chosen, Enter submits the form's `?s=` search as today.
Its option text includes the kind ("Belly, band, Providence, RI"), so screen readers hear it. The library's stylesheet is overridden in the site's look (card stock, hairline border, the active option on lavender). Without JavaScript the search box is the plain form it is today, because the library enhances an existing `<input>` rather than replacing the form.
*Alternatives:* writing our own ARIA combobox (rejected: the keyboard and screen-reader behavior is the hard part, and this library has it right); django-autocomplete-light with django-querysetsequence (rejected: built for choosing a form value, not going to a page, and brings Select2's look); django-htmx (helps render the list, not the accessibility); the browser's `<datalist>` (can't tag kinds or go to a link).

### 7. Indexable pages, a fuller sitemap
`noindex` is removed from `act_page` and `band.html` entirely. The sitemap lists `/bands` and every live act's page; held acts have no page, so they're excluded by the same `needs_review=False` filter.

### 8. The menu item by data migration
A data migration adds a "Bands & artists" `MenuItem` linking to `/bands` when none exists, so production gets it on deploy; editors can move or rename it in the admin.

## Risks / Trade-offs

- [Thin pages indexed: acts with only a name] → most live acts have MusicBrainz data, a bio or links; an act an editor thinks too thin can be held for review again in the admin.
- [3,100 entries on one page] → server-rendered text, no images; fine on phones. Pagination by letter is a later change if it grows tenfold.

## Migration Plan

Deploy with `import-curated-act-lists`; the menu item's migration runs on deploy. Rollback: revert; the menu item can stay or be deleted in the admin.
