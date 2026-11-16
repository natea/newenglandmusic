## Context

- Venues are `Venue` records kept in the admin (`add-massachusetts-regions` retired the daily sheet sync; `sync_venues_from_gsheets` is now a manual import, and fields the sheet doesn't own are never touched by it). A venue added in the admin gets the next `V` number. `is_active` is `None` for most venues (unknown) and `False` for closed ones; autocomplete and the submit form already treat only `False` as inactive.
- `Venue.location` gives "Allston (Allston Village), MA"; `Venue.google_maps_link` builds a Google Maps URL from the exact location or the place ID.
- Areas are defined in `core/geo_areas.py`; each Massachusetts venue is in exactly one sub-region (`area_q`), and a metro's listing is `/?metro=<slug>`. The public site lists only New England (`NEW_ENGLAND_STATES`, `new_england_q`).
- The band page (`core/templates/core/band.html`) has the card, tab and ruled show rows; `add-event-pages` moves the card styles into a `_card.scss` partial and adds `billing(event)` for headliner and openers.
- The chosen composition is `.impeccable/mocks/decision/poster-column.html`; its direction contract is in `.impeccable/surfaces/core-templates-core-venue-html.md`.

## Goals / Non-Goals

**Goals:** a venue page that leads with its bill and keeps booking one click away; addresses that don't change when a venue is renamed.

**Non-Goals:** a venues index or A–Z list; a map; venue search by type, size or genre (the "venue search" gap named in the group's email, a later change); editing venues from the page.

## Decisions

### 1. Slug stored on the venue, filled once
`Venue.slug` (unique `SlugField`), filled by `unique_slug` from the name, adding the town ("the-bar-portland") before falling back to `-2`. A data migration fills existing venues; `save()` fills a new venue's, but never rewrites an existing one, so renaming a venue in the admin keeps its address. The slug is an editable admin field (validated unique), for the rare deliberate change. The manual sheet import's field list doesn't include it.
*Alternative:* `/venues/<sheet_id>` ("V0820"). Rejected: unreadable.

### 2. The bill reuses the listing's billing
Each night is rendered from `billing(event)` (title line dropped on the bill, headliner, openers) and the event's start time, linking to `/event/<id>`. Shows come from `Event.objects` (approved) at this venue from the start of today, ordered by start time and `same_time_order_override`; an event with a venue override is still the venue's. Today's nights carry a lavender band, as in the sketch.
*Alternative:* embed the stored listing HTML. Rejected: the listing repeats the venue on every row and carries the description, which the bill drops on purpose.

### 3. Facts as two quiet sections below the bill
(Changed by `add-venue-list`, 2026-11-16: booking type, link and notes moved to the venue's artist view; "Playing here" keeps open mic, genres, niche and size, and the fact line's "Open booking" link goes to the artist view.)
"Playing here" and "Getting here" are definition lists in the card's field style (7.5em label column), each field drawn only when it has a value; booleans (open mic, family-friendly, LGBTQ+-friendly) are drawn only when true or false, as "Yes" or "No", never when unknown. The fact line above the bill is assembled from the same values, so they can't disagree.

### 4. New England's venues, and the sub-region
Only venues in New England (`new_england_q`) get a page; others answer 404, as their shows are hidden from the listings. For a Massachusetts venue, the fact line names its sub-region ("North of the Charles"), found by testing the sub-regions' `area_q` against the venue, and links it to `/?metro=<slug>`. Other states' venues show no metro.

### 5. Map link only
The fact line's "Map ↗" uses `Venue.google_maps_link`, opening Google's own page in a new tab; no tiles, no coordinates on our page (PRODUCT.md: Google Places display terms unsettled).

### 6. Links in, and search engines
The event page (from `add-event-pages`) links its venue name to `Venue.get_absolute_url()`; `VenueAdmin` gets "View on site" through that method. Listings stay at one link per row. The site can be shared now, so the page carries no `noindex` and has a canonical link to itself; adding venue pages to the sitemap is `improve-sitemap`'s work.

## Risks / Trade-offs

- [A venue is renamed, leaving an old-looking slug] → the slug is kept on purpose so links don't break; an editor can change it in the admin.
- [Busy rooms list 40+ shows, making a long page] → the bill is the point of the page; it groups nothing and paginates nothing, and the facts sit below it with an anchor link from the fact line.
- [Depends on `add-event-pages`] → build it after; if built first, its tasks include `billing()` and the card partial.

## Migration Plan

1. Migration adds `Venue.slug` and fills it; deploy runs it on Render.
2. Rollback: revert the deploy; the slug column is harmless if left.
