## Context

- Venues are `Venue` records synced from the sheet by `Venue_ID` (`sync_venues_from_gsheets`); fields the sheet doesn't own are never touched by the sync. `is_active` is `None` for most venues (unknown) and `False` for closed ones; autocomplete and the submit form already treat only `False` as inactive.
- `Venue.location` gives "Allston (Allston Village), MA"; `Venue.google_maps_link` builds a Google Maps URL from the exact location or the place ID.
- The band page (`core/templates/core/band.html`) has the card, tab and ruled show rows; `add-event-pages` moves the card styles into a `_card.scss` partial and adds `billing(event)` for headliner and openers.
- The chosen composition is `.impeccable/mocks/decision/poster-column.html`; its direction contract is in `.impeccable/surfaces/core-templates-core-venue-html.md`.

## Goals / Non-Goals

**Goals:** a venue page that leads with its bill and keeps booking one click away; slugs that never change under the sheet sync.

**Non-Goals:** a venues index or A–Z list; a map; venue search by type, size or genre (the "venue search" gap named in the group's email, a later change); editing venues from the page.

## Decisions

### 1. Slug stored on the venue, filled once
`Venue.slug` (unique `SlugField`), filled by `unique_slug` from the name, adding the town ("the-bar-portland") before falling back to `-2`. A data migration fills existing venues; `save()` fills a new venue's. The sheet sync's field list doesn't include it, so a renamed venue keeps its address.
*Alternative:* `/venues/<sheet_id>` ("V0820"). Rejected: unreadable, and venues added outside the sheet have none.

### 2. The bill reuses the listing's billing
Each night is rendered from `billing(event)` (title line dropped on the bill, headliner, openers) and the event's start time, linking to `/event/<id>`. Shows come from `Event.objects` (approved) at this venue from the start of today, ordered by start time and `same_time_order_override`; an event with a venue override is still the venue's. Today's nights carry a lavender band, as in the sketch.
*Alternative:* embed the stored listing HTML. Rejected: the listing repeats the venue on every row and carries the description, which the bill drops on purpose.

### 3. Facts as two quiet sections below the bill
"Playing here" and "Getting here" are definition lists in the card's field style (7.5em label column), each field drawn only when it has a value; booleans (open mic, family-friendly, LGBTQ+-friendly) are drawn only when true or false, as "Yes" or "No", never when unknown. The fact line above the bill is assembled from the same values, so they can't disagree.

### 4. Map link only
The fact line's "Map ↗" uses `Venue.google_maps_link`, opening Google's own page in a new tab; no tiles, no coordinates on our page (PRODUCT.md: Google Places display terms unsettled).

### 5. Links in
The event page (from `add-event-pages`) links its venue name to `Venue.get_absolute_url()`; `VenueAdmin` gets "View on site" through that method. Listings stay at one link per row.

## Risks / Trade-offs

- [Venue names in the sheet change, leaving an old slug] → the slug is kept on purpose; an editor can change it in the admin.
- [Busy rooms list 40+ shows, making a long page] → the bill is the point of the page; it groups nothing and paginates nothing, and the facts sit below it with an anchor link from the fact line.
- [Depends on `add-event-pages`] → build it after; if built first, its tasks include `billing()` and the card partial.

## Migration Plan

1. Migration adds `Venue.slug` and fills it; deploy runs it on Render.
2. Rollback: revert the deploy; the slug column is harmless if left.
