Issue: [#15 Incorporate the Google Calendar Simple API to generate calendars that people can subscribe to](https://github.com/natea/newenglandmusic/issues/15)

## Context

- `/calendar.ics` already serves live feeds for a region, state or metro (`core/views/calendar_feed.py`, `core/calendar_feeds.py`): stable UIDs, `STATUS:CANCELLED`, `REFRESH-INTERVAL` and `X-PUBLISHED-TTL` of six hours, an `ETag`. Apps refresh on their own schedule; Google may take up to a day, which no change on our side can speed up. The issue's idea of a library that creates Google calendars would not improve on this for subscribing, and only matters for the later sign-in ideas.
- The subscribe option is `core/templates/core/calendar_subscribe.html`, a `<details class="calendarSubscribe">` included in `index.html` after the area filter form and the location form, so it sits below two form blocks. `subscribe_links(geo_filter)` returns the feed's `https://` URL, its `webcal://` URL and Google's add-by-URL link. The view passes it as `calendar_links`.
- Venue pages do not exist yet: `add-venue-pages` specifies `/venues/<slug>` but is unbuilt.
- The user thread settled the scope: only make the existing subscribe option easier to find, near the top of the listing and on each venue's page.

## Goals / Non-Goals

**Goals:** a subscribe button that a visitor sees without scrolling or opening anything, on the listing and on venue pages, with the same three ways to subscribe.

**Non-Goals:** narrower feeds (venue, artist, genre), personal feeds of picked shows, Google sign-in, the Google Calendar Simple API, accounts, changes to feed content or refresh timing.

## Decisions

### 1. Keep the feeds and links; change where and how they show
The panel's contents (the webcal link, the Google link, the copyable address, the note that Google can take up to a day) are unchanged. What changes is the summary: a button-styled "Subscribe" that is visible near the top, replacing a plain-text summary below the filters. It stays a `<details>` (a `<summary>` styled as a button) so it works without JavaScript. The links keep their `calendarLink` and `google` classes, because `analytics.js` fires `calendar_feed_subscribed` on them; the venue button uses the same markup, so its clicks are counted in the same event (an open question covers telling them apart). *Alternative:* always-open links. Rejected for the listing: three links and a text field would push the calendar down.

### 2. Placement on the listing
The button moves to the top of the page content, inside the `content` block before the area filter include, so it is seen first on a phone as well. Where there is a page heading (month archives, venue pages) it sits level with it; the homepage hides its heading, so there it sits at the top of the content on its own. It still names the area chosen ("Subscribe: Vermont"). The exact layout is left to the sketches.

### 3. A venue's button subscribes to its state
Feeds exist only by area, so on a venue page the button links to the feed of the venue's state (`?state=<slug>`), and its label says which ("Subscribe: Massachusetts", the same form as the listing). `subscribe_links` takes a `GeoFilter`, and `Venue.state` is a two-letter code, so the venue view looks up the offered state area (`offered_areas("state", new_england_only=True)`) whose `states` hold that code, ignoring case, and passes `GeoFilter(state=area)`. If the code is blank or matches no offered area, it passes an empty filter, giving the all-areas feed. `subscribe_links` itself does not change. *Alternative:* the venue's metro or sub-region. Not chosen here because a state always exists for a venue; see the open question. A feed of just this venue's shows would be better for the visitor but is a narrower-calendar change, and is deferred.

### 4. Order of building
The listing part has no dependency. This change must be archived after `add-venue-pages`, since its `venue-pages` requirement is ADDED to a capability that has no main spec until then. The venue-page part is built after `add-venue-pages`; if that is not built when this one is, build the listing part and leave the venue tasks open.

### 5. Mocking in tests
No outside service is used. Tests render the pages with Django's test client and read the HTML; feed behavior is already tested in `core/tests/test_calendar_feeds.py` and stays untouched, except the two assertions there on the old "Subscribe to this calendar" wording, which are rewritten. A test also checks the control is a `<summary>` and the links keep their analytics classes. Nothing touches the network; Google Calendar's link is only checked as text, never fetched.

## Risks / Trade-offs

- A state feed from a venue page may be wider than the visitor expects. The label names the area to reduce that; the narrower feed is future work.
- A more prominent button competes with the area filter and the month calendar for attention at the top of the page. The design round decides the balance.

## Open Questions

- Which area should a venue's button subscribe to: its state (proposed), its metro or Massachusetts sub-region, or the all-areas feed?
- Should the button's use be counted in analytics (a click event)? Not included unless the owner asks.
- Should the month archive pages get the button in the same place as the homepage (proposed), or only the homepage?

## Sketches

- [Option A, "Button at the heading"](sketches/a.html). Thesis: a solid Subscribe button sits level with the page heading, top right on the listing and in the venue header, and opens a small card with the same links and address. Risk: the panel is still one click away and the button is small beside a big heading, so it may be missed on a phone.
- [Option B, "Always-open strip"](sketches/b.html). Thesis: a full-width strip under the heading shows every way to subscribe at once, with no click to open, on the listing and on venue pages. Risk: it takes a permanent band of height above the calendar and the area filter, pushing the shows down.
- [Option C, "Side card"](sketches/c.html). Thesis: a card in a right-hand rail explains what subscribing does and holds the button and links, beside the listing and the venue's shows. Risk: the rail has no room on a phone, where it drops below the content, and it makes the page two-column.
