## Why

A listing's navy underline now means three different things: a performer's band page, the venue's own page for the show, or (in a title with no linked performers) the venue's page again under a different look. Names aren't ranked either: a headliner and the third opener look the same, and an event whose title and artists both name its acts prints them twice ("Dev Lemons, Venus & the Flytraps: Dev Lemons, Venus & the Flytraps"). Most ticket links duplicate the "info" link (829 of 983 ticketed upcoming events point both at the same URL). The site has no page of its own for a show, so there is nowhere to put an event's acts, its venue facts and its links together.

## What Changes

- **Event pages.** Every event gets a page of its own at `/event/<id>`, which today only redirects into the calendar. The page is an index card like the band pages: the date and time, the show's title when it adds something, the headliner and the openers (each linked to its band or artist page when it has one, with their play buttons), the venue with its town, age policy and access notes, the description, the calendar/map/share/save icons, and "Tickets ↗" and "Venue's page ↗" links, shown as one link when they're the same URL. Every event has one, with performers or without. Pages are `noindex` while the site is unshared. Unapproved events answer 404. Share links, calendar feeds and the band pages already point at `/event/<id>`, so they land on the page.
- **BREAKING (for visitors): the listing's headline links to the event page, not out to the venue.** One link per row goes to our own page; the tix badge stays the one-click way out to tickets. The "info ↗" link leaves the listing.
- **Act names in a listing aren't links.** A performer's name in a listing is plain text; its band or artist page is one click away, on the event page. (Default chosen pending review: opener names unlinked.)
- **Headliner and openers.** The listing's headline is the first-billed act, bold and one step larger than body text; openers follow in regular weight after "with". The show's own title ("Halloween Show", "20 Years of Nekrogoblikon") becomes a small grey line above the headline, only when it says something the names don't. A name given by both the title and the artists is printed once.
- **Unchanged:** the URL stays numeric, `/event/<id>` (default chosen pending review; a readable slug can be added later); the listing stays a dense text row (no cards, no thumbnails); the icon row, play buttons, price, venue, distance and description stay where they are; the day map keeps reading the listing's `data-` attributes.

## Capabilities

### New Capabilities
- `event-pages`: the public page for one event at `/event/<id>`: what it shows, its links, which events have one, and how it reads on phones and to search engines.
- `event-listing`: how an event's row in the calendar, Saved shows and search results is laid out: the headline and its link, the headliner and openers, the show's title line, repeated names, and the ticket badge.

### Modified Capabilities
- `band-pages`: "Events link to their acts" changes. Listings no longer link performer names or carry an "info" link; acts are linked from the event page instead. (The `band-pages` spec arrives with `add-band-pages`, which is finished and must be archived before this change.)

## Impact

- **Code:** `core/views/event_redirect.py` becomes the event page view (the share-preview metadata stays); a new `core/templates/core/event_page.html` and `core/static/core/scss/event_page.scss`, reusing the band page's card, strip and show-row styles; `core/templates/core/event.html` (the listing) and `core/event_performers.py` (`listing_parts`, which now orders the headliner and openers instead of linking them); `core/artist_names.py` for headliner/opener splitting and repeated names.
- **Stored HTML:** every event's listing is stored rendered, so the change ships with a `resave_all_events` run, locally and on Render (about 3,300 events in production).
- **Unchanged contracts:** the `/event/<id>/ics` and `/event/<id>/gcal` routes, the icon row (built per page, `event-action-icons`), saved shows, calendar feeds' event URLs, and the day map's `data-` attributes.
- **No new data, APIs or migrations.** Everything shown already exists on the event, its venue and its performers.
- **Order:** archive `add-band-pages` first, since this change modifies its `band-pages` spec.
