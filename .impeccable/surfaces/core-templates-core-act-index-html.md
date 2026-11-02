---
version: 1
slug: "core-templates-core-act-index-html"
primary_target: "core/templates/core/act_index.html"
related_targets: ["core/templates/core/search.html"]
---

# Bands & artists index and search results

## Scope and mode

`/bands` (every live band and artist, A to Z) and the search results page (`/?s=`): mode **Operate**. The visitor is looking up a name they already know; browsing by next show is secondary. Inside the site's established world (DESIGN.md: warm grey ground, card stock, plum tab, lavender strip, ruled blue, navy links).

## Audience, job and content

- Fans and musicians finding one act's page fast; editors checking an act exists.
- Per act: name (link), kind, home town or MusicBrainz area, next upcoming show's date. About 3,100 acts; most have no show.
- Search: bands and artists, venues, upcoming shows (soonest first) then past shows (newest first), static pages. Every listed event keeps its action icon row (event-action-icons spec).

## Direction contract

THESIS: the listing is the index at the back of a reference book: names run in two tight columns, each entry carrying its next show as its page reference; it refuses the card grid and the one-name-per-row table.

OWN-WORLD: one card-stock card on the grey ground under the plum "Bands & artists" tab; a lavender letter rail; each letter opens with a large plum Helvetica initial; entries are a bold navy name, kind and town in small quiet grey, a dotted hairline leader and a bold tabular date; ruled-blue column rule; guide words in small caps over each block.

STORY: the visitor jumps to a letter, scans the guide words to the right block, runs an eye down a column to the name, and follows it; on search the same entries answer what was typed, then compact show rows.

FIRST VIEWPORT: site header; tab; count; letter rail; the first block's guide words; the plum initial and two columns of about twenty entries each.

FORM: back-of-book index, structure 6 of 7 on the ranked list, seed:859d822c18cda29d.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md updated for the index and search.

## Unresolved

- None. Names starting "The" are inverted in the index only ("Blue Stones, The"), as the user chose; pages, search and suggestions keep the act's own name.
