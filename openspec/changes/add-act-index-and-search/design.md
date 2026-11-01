## Context

- Act pages: `core/views/act_page.py` sets `noindex` when the act has no upcoming show; `band.html` writes the meta tag. The sitemap (`core/sitemap.py`) lists only acts with an upcoming approved show.
- Search: `core/views/search.py` runs Postgres full-text search over events and static pages; the homepage hands `?s=` to it. No spec covers search yet (it came with nyc noise).
- The menu is `MenuItem` rows (an `OrderedModel`), edited in the admin.
- `import-curated-act-lists` adds `needs_review`; held acts already have no page.

## Goals / Non-Goals

**Goals:** every live act reachable by browsing and by search, on and off the site.

**Non-Goals:** filters on the index (by source, genre, state; the admin has the source filter); pagination; venue pages.

## Decisions

### 1. One index for bands and artists, at `/bands`
Visitors look for a name, not a kind, so both kinds share one A–Z list, each entry labelled. `/artists` redirects there rather than duplicating it.
*Alternative:* separate `/bands` and `/artists` indexes. Rejected: a visitor looking for "Anjimile" shouldn't have to know she's filed as an artist.

### 2. One query, grouped in Python
`Band` and `Artist` rows with `needs_review=False`, each annotated with its next upcoming approved show (`Min("performances__event__starttime")` filtered to approved events from the start of today), merged and sorted by name with a leading "The" dropped, grouped by first letter (`#` for anything else). At about 3,100 acts this renders in one page without pagination; the letter rail is the navigation.

### 3. The site's index-card look
The index is the band page's card: "Bands & artists" on the plum tab, a lavender letter rail (letters with no acts drawn quiet, not linked), and entries as ruled rows: the name bold and linked, then "Band · Providence, RI" in quiet grey, and the next show's date right-aligned in tabular figures. No design round: it's a list inside the established world (DESIGN.md), with the card, tab and ruled rows it already defines.

### 4. Acts in search by name match
`unaccent` + `icontains` on the name (the `unaccent` extension is installed with `pg_trgm`), live acts only, limited to 20, ordered by name; rendered above the events as "Bands & artists". Full-text search isn't used for names: a name is one phrase, and partial matches ("bell" finding Belly) are what visitors expect.

### 5. Indexable pages, a fuller sitemap
`noindex` is removed from `act_page` and `band.html` entirely. The sitemap lists `/bands` and every live act's page; held acts have no page, so they're excluded by the same `needs_review=False` filter.

### 6. The menu item by data migration
A data migration adds a "Bands & artists" `MenuItem` linking to `/bands` when none exists, so production gets it on deploy; editors can move or rename it in the admin.

## Risks / Trade-offs

- [Thin pages indexed: acts with only a name] → most live acts have MusicBrainz data, a bio or links; an act an editor thinks too thin can be held for review again in the admin.
- [3,100 entries on one page] → server-rendered text, no images; fine on phones. Pagination by letter is a later change if it grows tenfold.

## Migration Plan

Deploy with `import-curated-act-lists`; the menu item's migration runs on deploy. Rollback: revert; the menu item can stay or be deleted in the admin.
