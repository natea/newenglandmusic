## Context

`MusicAct` (abstract; `Artist`, `Band`) holds names, origin, website and Bandcamp, MusicBrainz data, `field_sources`, and Wikipedia's paragraph. `EventPerformer` (from `add-artists-from-events`) links events to acts in billing order. `core/wikipedia.py` asks Wikidata for an item's English article and Wikipedia for its summary, paced, with the contact user agent. Event listings are stored as baked HTML (`core/utils_event_caching.bake_event_html`, re-rendered on save); `/event/<id>` redirects to an event on the calendar, and `/saved/toggle/<id>` saves it. The site's look lives in `core/static/core/scss/` (warm grey `#d4d0c7`, Open Sans and Helvetica-style headings, navy links, lavender strips, purple month bar) with no DESIGN.md yet.

The page's direction was chosen on Impeccable's decision page on 2026-10-29: the record-store index card, whose contract (thesis, palette, first viewport, story) is in `.impeccable/surfaces/core-templates-core-band-html.md` and whose sketch is `.impeccable/mocks/decision/lead-index-card.html`.

## Goals / Non-Goals

**Goals:** a page per act that answers "when do they play next" and "who are they" in the site's own look, honest about sparse data, and correct about every licence.

**Non-Goals:** play buttons on the page; band self-editing; past shows; anything from Last.fm or Bandcamp beyond links.

## Decisions

**1. One template, two kinds.** `band.html` renders a `MusicAct`; an artist's page swaps "Members" for "Bands" and the tab's word. Views `band_page(slug)` and `artist_page(slug)` with `get_object_or_404`. `slug` is a `SlugField`, unique per model, set on save from the name (`slugify`, with `-2`, `-3` on collision), backfilled in the migration.

**2. The card.** As the sketch, with two changes made while building: the card takes the site's own 42em column, and the act's name is the tab itself (white heavy type on purple, as a record-store divider prints the name on its tab) instead of a tab carrying the kind above the name, since a label above a heading is on Impeccable's ban list. Site header; the card on the grey ground; the name at about 3.4rem in the heading face; a meta line; the lavender next-show strip; a definition list of fields (bold grey labels in a fixed column, collapsing above the values below 600px); the bio on faint ruled lines with its credit; then the full show list; then, when something's missing, the invitation in small grey type. Members show a 48px headshot only when they have one; otherwise names alone, no placeholder silhouettes. On phones the order is name, meta, next show, then the rest, which the sketch's order already gives.

**3. Photos from Commons, credited, hot-linked.** Wikidata P18 gives a file name. Commons' `imageinfo` with `iiprop=extmetadata` gives `LicenseShortName`, `LicenseUrl`, `Artist` (HTML, stripped to text) and `UsageTerms`. Accepted when the licence short name starts with "Public domain", "CC0", "CC BY " or "CC BY-SA " (the free licences Commons uses; it hosts nothing else, but the check keeps an unusual tag out). Stored: `photo_file`, `photo_author`, `photo_license`, `photo_license_url`. The page loads `https://commons.wikimedia.org/wiki/Special:FilePath/<file>?width=640` (members at 96), which Wikimedia serves and allows embedding, with `loading="lazy"` and an `alt` naming the act; the credit under it links the file page and the licence. No image is copied to the site, so nothing to re-licence or expire.

**4. Social links.** MusicBrainz url-rels: type "social network" whose host is `instagram.com`, and types "youtube" or "video channel" on `youtube.com`. Wikidata: P2003 → `https://www.instagram.com/<name>/`, P2397 → `https://www.youtube.com/channel/<id>`. MusicBrainz first, Wikidata second, an editor's always (marked in `field_sources`). These come from the same Wikidata `wbgetentities` call as the image (`props=claims|sitelinks`), so the introduction's article lookup and these share one request.

**5. Linking performers on the calendar.** `event.html` renders the Artists text; names that resolve to the event's performers (by `name_key`, in order) render as links to their pages. Because listings are baked, linking or unlinking a performer re-bakes that event: `link_from_names` and the admin inline call `bake_event_html` for events whose links changed, and a one-off `resave_all_events` after deploy bakes the rest.

**5a. As built (2026-10-29).** An event's own link (to its venue or ticket page) wrapped its whole title and artists text, and links can't nest: when an event has performers, its link covers only the title, and the artists text is split (keeping the separators) into plain text and performer links (`core/event_performers.artist_parts`). Deleting an artist or band re-renders the events that linked it, through `pre_delete` and `post_delete` signals connected in `CoreConfig.ready`, so a listing never points at a page that's gone; this catches the admin's bulk "delete selected" too, which skips a model's own `delete()`.

**6. The invitation.** A `mailto:` to `API_CONTACT_EMAIL` with the subject "<name> on New England Music" and the page URL in the body. Shown when the photo, bio or links are missing. A form is a later change.

**7. Visual system.** The page adds `band.scss` using the site's existing values; no new palette or face. The card's off-white (`#f6f4ee`), hairline (`#b9b4a8`) and ruled-line blue (`#c9d3e6`) are the only additions, recorded in DESIGN.md at the finish (Impeccable's documenter records the incumbent system plus these).

**How it's tested.** View tests for a full band, a sparse band, an artist, a 404, the next-show strip and the list (approved only, upcoming only, ordered), current and former members, links shown only when set, the photo and its credit, a disambiguation-only bio, the invitation, and the template's text alternatives and title; enrichment tests with recorded Wikidata and Commons answers (free, non-free, missing image; social links; an editor's link kept); a calendar test that a performer's name links and others don't. A Playwright check renders the page at 1440 and 390 wide for no sideways scroll and the next show in the first screen. Nothing reaches the network.

## Risks / Trade-offs

- **[A wrong act's photo]** A mis-matched MusicBrainz record brings the wrong band's photo. → The photo comes only with a match an editor can clear; the admin shows the photo so a wrong one is obvious.
- **[Commons is unavailable]** The page's photo fails to load. → The card has no layout dependency on it; the image has dimensions and the credit stays as text.
- **[Name collisions in slugs]** "Horse" the band and "Horse" the artist are different kinds and paths; two bands with one name get `-2`.
- **[Thin pages indexed]** Hundreds of sparse pages. → Pages without upcoming shows get `noindex`; the sitemap lists only acts with upcoming shows.

## Migration Plan

Merge after `add-artists-from-events`. Migrate (slugs backfilled), run `enrich_artists_from_musicbrainz --refresh` for photos and social links (about 2 more requests per record with a Wikidata item), then `resave_all_events` to link performers in the listings.

## Open Questions

- The invitation's address: `API_CONTACT_EMAIL` (newenglandmusic843@gmail.com) for now, unless another inbox should take band submissions.
