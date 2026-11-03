Issue: [#9 Create venue page and venue listing](https://github.com/natea/newenglandmusic/issues/9)

## Why

The site keeps about 730 editor-curated venues, but a visitor can't browse them or find one: venues show only as a name in event listings (`add-venue-pages` gives each venue a page, but nothing lists them). Fans want to look through the rooms in their area; bands want to find rooms that will take them and learn how to ask. GitHub issue 9 asks for both: a venue page and a venue list that serve fans and artists.

## What Changes

- **A venue list for fans** at `/venues`: every active venue, alphabetical, each linking to its page, with its town and state, kind and size of room and genres. It narrows by place the way the homepage events do (region, state, metro area, towns and neighborhoods) and by genre.
- **An artist filter on that list:** "Takes open bookings" narrows it to venues marked as taking open bookings, so a band can find rooms to approach. It sits apart from the fan filters, under its own "For artists" heading.
- **A separate artist view of each venue** at `/venues/<slug>/booking`, beside the fan page and reached from a "For artists" tab on it (the fan page is the other tab). It carries what the sheet already records for booking: whether the venue takes open bookings, what kind of booking it does, how to apply (booking link, or else website) and the venue's notes, plus open mic, size and genres. Booking details move off the fan page to here; the fan page keeps a short link to it.
- **A "Venues" menu item** pointing to the list.
- **No new data.** Extra artist-side details (typical capacity, house sound system, pay norms) are not collected and are not part of this change; the thread chose a separate view of what exists.

## Capabilities

### New Capabilities
- `venue-list`: the public, alphabetical, filterable list of venues, and the artist filter for open bookings.
- `venue-booking-view`: the artist-facing view of one venue's booking details, and how it relates to the fan page.

### Modified Capabilities
- `event-geo-filter`: the remembered-filter cookie also covers `/venues` (a MODIFIED delta of "The site remembers a visitor's last filter"). The fan page's booking fields belong to `add-venue-pages`, which is unarchived, so their move is made there, see design.

## Impact

- **Code:** a new `core/views/venue_list.py` and `core/views/venue_booking.py`, templates `venue_list.html` and `venue_booking.html`, a shared "fan / for artists" tab partial, styles in the site's index-card style; `core/geo_filters.py` is reused as it is for place filters (`GeoFilter.q(prefix="")` already builds a venue query); the shared place form gains hidden fields that carry the genre and open-booking filters; a URL for each; a "Venues" menu item (a `MenuItem` row through a data migration).
- **Order:** builds after `add-venue-pages`, which is the single owner of `Venue.slug` (with its migration), `get_absolute_url` and the fan page; `improve-sitemap` must take the slug from it rather than add its own. Editing `add-venue-pages` so its fan page links to the artist view (task 1.1) is a hard prerequisite: it must be done and validated before this change is accepted or applied.
- **No schema change, new data source, API or paid call.** Everything shown is already in the venue record.
