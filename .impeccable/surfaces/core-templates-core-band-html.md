---
version: 1
slug: "core-templates-core-band-html"
primary_target: "core/templates/core/band.html"
related_targets: []
---

# Band page

## Scope and mode

The public page for one band (`Band`), and by extension one artist (`Artist`): mode **Read**. The visitor wants to know who the band is and when they next play in the Northeast. Inside the site's established world (warm grey ground, bold sans, navy underlined links, lavender strips, purple bars, one narrow column).

## Audience, job and content

- Fans deciding whether to go: the next show matters most, then who the band is. On a phone the next show comes right after the name.
- Musicians and editors checking an act: members, links, where they're from.
- Content per band: name; kind and genre; home town or MusicBrainz area and formed year; bio (Wikipedia's opening paragraph, credited, or MusicBrainz's disambiguation note); links (website, Bandcamp, Instagram, YouTube); members with roles and years, current then former, with headshots when a freely licensed one exists; a photo only when a freely licensed one exists on Wikimedia Commons, credited; upcoming shows (date, venue, town) from event performers.
- Most local bands have only a name and a few shows: the card then shows only what exists, plus a quiet line inviting the band to send a photo, bio and links.

## Direction contract

THESIS: each band is a filed index card, a purple name tab over a card of typed fields, so a sparse local act and a famous one read as the same honest record; it refuses the hero-photo artist page with a big banner and empty modules.

OWN-WORLD: the site's warm grey ground (#d4d0c7) with one off-white card (#f6f4ee) on it, hairline border #b9b4a8; a purple tab (#8b5d8b) carrying the kind in spaced caps; heavy Helvetica-style display for the name; field labels bold grey in a fixed left column; bio set on faint blue ruled lines; lavender (#eeeeff) strip for the next show; navy underlined links; no shadows beyond a 1px bottom edge, no rounded corners.

STORY: the visitor sees the band's name and its next Northeast show at once, reads who they are from the fields and the bio, and leaves with a show saved or a link followed.

FIRST VIEWPORT: site header; then the card, 46em wide, centred: the purple tab, the band name at about 56px, a one-line kind, genre, origin and year; the lavender next-show strip (date, venue, town, details, count of more shows) as the primary action; fields for members, links and photo; the bio on ruled lines with its credit.

FORM: record-store index card, position 7 of 7 on the ranked list, seed:af4a532c16c3cd21.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved

- How a band sends more (a form, an email address, or a link to submit) is decided in the OpenSpec proposal.
- The artist page reuses the card; its field set (bands they're in instead of members) is part of the same proposal.
