---
version: 1
slug: "core-templates-core-venue-html"
primary_target: "core/templates/core/venue.html"
related_targets: ["core/views/venue_page.py"]
---

# Venue page

Scope: the public page for one venue, `/venues/<slug>`. Visitor mode: Read. Audience: fans deciding whether to go, and musicians deciding whether to ask for a show, served equally. Location is shown as town and neighborhood text with a link out to Google Maps; no embedded map until the Google Places display terms are settled.

## Direction contract

THESIS: A venue page is the room's own show bill. The coming shows lead, date by date, the way the venue's monthly poster reads; it refuses the directory-listing default where a fact table and a photo sit above a buried event list.

OWN-WORLD: the site's world, unchanged: warm grey ground, card stock with a 3px plum top edge, the venue's name on the plum tab, navy underlined links, Helvetica-bold names, tabular dates, 1px ruled-blue rules between nights, lavender only where the visitor acts (tonight's row, the booking link).

STORY: a fan sees what's on and when within one glance and saves or opens a night; a musician sees in one line what the room books and how to ask, and follows the booking link.

FIRST VIEWPORT: name tab; a single fact line (size and kind of room · neighborhood, town, state · Map ↗ · what it books) ending in a lavender "Open booking: <how> ›" link when the venue takes new acts; then "The bill", with the show count, and eight or so nights: a big tabular day number over a lowercase weekday and month, the headliner bold at about 1.4rem, "with" openers below in quiet grey, the time at the right; tonight's night on lavender.

FORM: gig-poster column, third on my ordered list of seven. seed: none (unavailable)

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

- Where the full booking and access facts sit below the bill (a "Playing here" and "Getting here" pair is the working plan).
- Whether listings link venue names to the page (the event-pages change keeps listings to one link per row).
