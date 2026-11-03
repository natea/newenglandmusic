Issue: [#9 Create venue page and venue listing](https://github.com/natea/newenglandmusic/issues/9)

## Context

- `Venue` already holds everything shown: `city_town`, `state`, `neighborhood`, `venue_type`, `size`, `genres` (a list, `["ALL"]` for venues that book anything), `open_booking` (null when unknown), `booking_type`, `booking_url`, `booking_notes`, `open_mic`, `website`, `is_active` (only `False` means closed). See `core/models.py`.
- The homepage filters events by `GeoFilter` (`core/geo_filters.py`): region, state, metro, towns and neighborhoods, from URL parameters, with a remembered cookie and a redirect so the address always shows the filter. Its form is `core/templates/core/geo_filter_form.html`. `GeoFilter.q(prefix=...)` already builds a query for a venue (`prefix=""`) or an event (`prefix="venue__"`).
- The A–Z index of acts (`core/views/act_index.py`, from `add-act-index-and-search`) is the site's pattern for a long alphabetical list: letter rail, "The" ignored, index-card style.
- `add-venue-pages` (unarchived) gives each venue `Venue.slug`, `get_absolute_url` and a fan page at `/venues/<slug>` that currently also carries "Playing here" booking fields and an "Open booking" link in its fact line.
- The thread (issue 9) decided: a separate artist view beside the fan view; an alphabetical fan list filtered by town and genre like the homepage; a special artist filter for venues taking open bookings.

## Goals / Non-Goals

**Goals:** a browsable, filterable list of venues; an artist view of booking details; no new data.

**Non-Goals:** collecting new artist-side details (capacity, house sound, pay or door-split norms) in the sheet; a map of the list; sorting by distance or by next show; sitemap or search-engine listing (the site is unshared); letting artists submit booking requests through the site; venue search (the search box change covers that).

## Decisions

### 1. Two new pages, no schema change
`/venues` is `venue_list` and `/venues/<slug>/booking` is `venue_booking`, as plain views over `Venue`. No model or migration change: the list needs only existing fields and `Venue.slug` from `add-venue-pages`.
*Alternative:* one venue page with JavaScript tabs. Rejected: tabs would hide booking details from a link and from no-JavaScript visitors, and a linkable address per view is what lets the list send artists straight to it.

### 2. Tabs are two links
"For fans" and "For artists" are a shared partial of two links with `aria-current` on the current one, used by both pages. Each view is its own page with its own title.

### 3. Place filters reuse `GeoFilter`
The list parses place parameters with `geo_filter_for_request` and applies `geo_filter.q()` to `Venue.objects`, and renders `geo_filter_form.html` (its form posts to `request.path`, so it works on `/venues`). It shares the homepage's cookie, so a returning visitor sees the same area on both; the `event-geo-filter` spec is modified to say so. Two things would otherwise lose the other filters: the remembered-place redirect (which carries only place parameters) and the place form (a plain GET form, whose "show all" link is `?clear=1`). So on `/venues` the redirect appends `genre` and `open_booking` (genre URL-encoded, since values such as "R&B" and "Rock/Pop" would break the query) to the remembered place, and the partial takes an optional list of extra parameters, drawn as hidden inputs, so changing the place keeps them. The form's script disables empty fields before submit, so the hidden inputs are only drawn for non-empty values. That script also decides "all place fields empty" with `fields.some(field => field.value)`, and a non-empty hidden `genre` would make that true, so choosing "All" would disable the empty place selects and the bare `?genre=Jazz` would redirect back to the remembered place. So the extra inputs are marked (`data-extra`) and the script's check and disabling cover only the place fields; with every place field "All" the empty place parameters are sent along with the genre, which clears the cookie. "Show all" clears the place only: the place form's clear link (`?clear=1`, which `geo_filter_for_request` handles before anything else) carries `genre` and `open_booking` too, so it never drops them. That link is drawn only when a place filter is set, so the list's empty state has its own "show all" link that clears every filter and works when only genre or open booking is set. The genre and open-booking controls clear themselves. The form partial's town lists are built from the same helpers the homepage view uses; those context pieces move into one helper both views call so they can't drift.
*Alternative:* a separate cookie for venues. Rejected: it would make "my area" two settings.

### 4. Genre filter and the "ALL" genre
`?genre=Jazz` matches venues whose `genres` contains the value or contains `"ALL"`, ignoring case. `genres` is an `ArrayField`, whose `contains` is case-sensitive, so the match is made in Python over the place-filtered venues (about 730 rows, as in decision 6), comparing case-folded values. Choices are the distinct genres across non-inactive venues, case-folded to one choice each (shown in the first spelling met), sorted, without "ALL". An unknown value is ignored. The genre is a URL parameter only, not remembered.

### 5. Open booking means `open_booking is True`
`?open_booking=1` keeps venues with `open_booking=True`. Unknown (null) is not included: the filter exists so an artist finds rooms that want them, and a false positive wastes their time. The list shows, under that filter, the booking type's label on each entry so an artist can skim (the spec requires it). Entries link to `/venues/<slug>/booking` under this filter; that is this change's reading of the thread, not something it asked for.

### 6. Active and ordering
Inactive means `is_active=False`, as in autocomplete and `add-venue-pages`: the query is `exclude(is_active=False)`, never `filter(is_active=True)`, which would drop venues whose status is null. The list is ordered in Python by the act index's `sort_name` rule (case-insensitive, leading "The" ignored), grouped by letter with a rail. About 730 venues in one query; no pagination (the act index pages its two-column layout, and may be reused).

### 7. Booking details move off the fan page
The artist view owns booking type, link, notes and the open-booking answer. This conflicts with `add-venue-pages`' "Playing here" section and fact-line link, which are still unbuilt. Rather than leave two homes for the same facts, task 1.1 edits that change's spec, design and tasks, and it is a hard prerequisite: that edit must be made and validated before this change is accepted or applied. It removes the "Playing here" booking fields and the fact-line "Open booking" link, and the scenarios "Open booking" and "Closed booking" of its venue-pages spec, replacing them with a link to the artist view; and it leaves the fan page's tab (its chosen mock) as the shared "For fans / For artists" partial this change defines, built there once and reused here. `add-venue-pages` is also the only change that adds `Venue.slug`. If `add-venue-pages` has already been built, the same edit is made in code and tests, and the main spec is updated by a delta in this change.
*Alternative:* show booking details on both pages. Rejected: it defeats the separate artist view the thread chose and duplicates text that changes in the sheet.

### 8. Booking type in plain words
`Venue.BookingType` labels ("Submit an Artist", "Locals Only", "Dart Throw") are the sheet's own and unclear to a stranger, so the artist view adds a one-line meaning for each type from a small table in code. "Unknown" is not drawn. The wording of those meanings is invented copy, not the sheet's, so the owner is asked to approve it (see Open Questions).

### 9. What the artist view shows beyond the thread
The thread asked for whether the venue takes bookings, how to apply and notes. The view also shows open mic, room size, genres and niche notes. This is a deliberate small addition: they are existing fields that tell an artist whether the room suits them, and no new data is needed. They can be dropped without touching anything else.

### 10. Search and the sitemap
The list and the artist view carry a per-page `noindex` and stay out of the sitemap, matching `add-venue-pages`. If `improve-sitemap`'s site-wide indexing switch lands, both follow it and the per-page tag becomes redundant. Its venue section must also skip `/booking` addresses. `improve-sitemap` also plans its own venue page at `/venue/<slug>/`; that page and route must be dropped or redirected to `/venues/<slug>`, or each venue gets two fan pages (task 1.2).

### 11. Routing
`/venues/<slug:slug>/booking` is registered beside the fan page route, and `/venues` and both venue routes go before any catch-all static-page route in `core/urls.py`. `/bands/` and `/artists/` redirect a trailing slash away (`without_trailing_slash`); `/venues/` and `/venues/<slug>/booking/` do the same, so a typed slash doesn't 404. A test checks that a venue whose slug is a word the site reserves doesn't shadow `/venues/booking` or other routes.

## Risks / Trade-offs

- [Few venues have `open_booking` filled, so the artist filter may look empty] → the "nothing matches" message says only venues marked as taking open bookings appear; coverage is a sheet-editing matter, not code.
- [Sharing the homepage cookie surprises someone who sets Vermont for events and sees few venues] → the form shows the active filter with "show all", as on the homepage.
- [Depends on `add-venue-pages` and edits its plan] → build it after; task 1.1 reconciles the two before any code.

## Migration Plan

1. Data migration adds a "Venues" `MenuItem`, as the act index did for "Bands & artists".
2. Rollback: revert the deploy; the menu row is harmless and can be deleted in the admin.

## Mocking in tests

No outside service is called. Tests build `Venue` and `GeoArea` rows directly and never touch Google Sheets (`gog`), Google Places, venue websites, Anthropic, ticketing or music APIs. The suite runs with outbound network blocked as the rest of it does.

## Open Questions

- Does the owner approve the plain-words meanings of the six booking types (decision 8)?
- Is the owner content that the booking fields leave the `add-venue-pages` fan page (decision 7), overriding what was proposed there?

- Should the artist view also list the venue's recent past shows, as a sign of what the room books? Left out here; adding it later changes only the artist view.
- The artist view shows `booking_notes`, which come straight from the sheet and may hold contact details; `improve-sitemap` keeps them off public pages. Is the owner content to show them (they are the "notes" the thread asked for), or should they wait until the sheet's notes are checked?
- The "Venues" menu item, the homepage cookie shared with `/venues` (decision 3) and the genre not being remembered (decision 4) are this change's readings; the thread said only "similar to how you can filter the events on the homepage". Does the owner agree with each?
- Does an editor want a "Last checked" date on booking details? The sheet has none, so none is shown.

## Sketches

Three static sketches of the list and the artist view (1440×900):

- [Option A: Index-card A–Z](sketches/a.html): extend the act index's letter rail and index-card look, with fan filters in one strip, a separate "For artists" row, and the artist view as a plain facts card.
- [Option B: Filter sidebar and table](sketches/b.html): a dense table with a filter sidebar where "For artists" is its own group, and a booking-type column linking to the artist view.
- [Option C: Audience switch](sketches/c.html): one list with an "I'm going out / I'm playing" switch that turns on the open-booking filter, and an apply-first artist page.
