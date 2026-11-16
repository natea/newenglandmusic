## Context

- `/event/<id>` is `core/views/event_redirect.py`: it renders `core/empty.html`, a page of share-preview metadata that redirects to `/<month>/#event-<id>` (one second late for Telegram's bot). The share icon (`core/event_actions.py`), calendar feeds (`core/calendar_feeds.py`), the weekly email (`core/digest.py`) and the act page's show rows (`core/templates/core/band.html`) link there by the `event_redirect` URL name; search results' show rows (`core/templates/core/search_show.html`) by the plain path.
- A listing row is `core/templates/core/event.html`, rendered once and stored in `Event.baked_html_template` by `bake_event_html` (`core/utils_event_caching.py`). Its icon row is a placeholder filled per page (`event-action-icons`). Since `add-band-pages`, `listing_parts` (`core/event_performers.py`) splits the title and artists into pieces and links the performers' names, and `rebake` re-renders an event when its performers change. Since `add-bandcamp-embedded-player`, the row's play buttons also include a Bandcamp button for each performer with a usable player (`event_bandcamp_players` in `core/artist_previews.py`), so the row depends on its performers for that too.
- `event_artist_names` (`core/artist_names.py`) already reads an event's acts in order: the title's names first, then the artists', without repeats, with kinds of night, tours and notes dropped.
- The day map (`core/templates/map/map.html`) reads each row's `data-` attributes and clones rows into its popups.
- The band page (`core/templates/core/band.html`, `core/static/core/scss/band.scss`) defines the index card: the plum tab, card stock, the lavender strip with the icon row, ruled show rows.

## Goals / Non-Goals

**Goals:**
- One meaning per link in a listing, with the band pages one click away on the event page.
- A listing's act names stop being links, so a row means one thing: the show.

**Non-Goals:**
- A readable slug in the event URL (`/event/123` stays; a slug can be added later without changing these specs).
- Venue pages. The event page shows the venue's name and facts, not a link to a venue page that doesn't exist yet.
- Changing which events are approved, or the event admin.

## Decisions

### 1. The redirect view becomes the page, at the same URL
`/event/<id>` renders `core/event_page.html` for an approved event and answers 404 otherwise (`Event.objects`, approved only). Its share metadata (`get_meta`, title "<time> @ <venue> - <acts>") moves into the page's head unchanged, so previews look the same. The URL name changes from `event_redirect` to `event_page`; its callers (the share icon, calendar feeds, the weekly email and the act page) are updated, and search results' plain `/event/<pk>` path already matches. `core/empty.html` and the Telegram delay go with the redirect.
*Alternative:* a new `/events/<id>` with the old address redirecting to it. Rejected: every link that exists already points at `/event/<id>`, and two addresses for one page splits share counts for nothing.

### 2. One function reads the billing: title line, headliner, openers
A new `billing(event)` in `core/artist_names.py` returns `(title_line, headliner, openers)` from `event_artist_names(event)`. The headliner is the first name, the openers the rest. The title line is the event's title when, after removing the presenter prefix and every act name and separator from it, words remain that aren't joiners ("with", "and", "&", "presents", "special guests") or punctuation; otherwise it's empty. With no act names at all, the headliner is the title (or the artists text), so a kind of night still has a headline. Both the listing and the event page use it, so they always agree.
*Alternative:* keep `listing_parts`, which preserves the source text's exact pieces and separators. Rejected for the listing: it can't rank acts, and it prints a name the title and artists both give twice. It stays for nothing else and is removed with its tests.

### 3. The listing is still stored HTML, and stops naming performers
`event.html` renders: an optional `.event-title-line` (small, quiet), then the headline as `<a class="event-headline" href="/event/<id>">` holding the headliner in a bold, larger `<b>`, then `with <openers>` in regular weight, then price, venue, age policy and town, description and access notes as now. The `hyperlink` no longer wraps anything and the `info ↗` link is removed. `listing_parts` and `linked_parts` go. Performer-driven re-rendering (`rebake` and its signals) **stays**: the row's Bandcamp buttons come from the event's performers, so a performer change still changes the row.
*Alternative:* render rows per request. Rejected: the stored HTML is what keeps the homepage fast (about 2,300 upcoming rows).

### 4. The event page reuses the band page's card
`event_page.html` extends the base template and draws one card: the date and time as the plum tab (display type, "Thu Oct 30 · 7:00 p.m."), the title line, the headliner (larger, linked when a performer) and openers (linked when performers) in the lavender strip with the icon row, then a field list (Venue, Price, Ages, Access, Links) and the description, then the play buttons. Performer links come from `event.performers` matched to the billing names by normalized name (with the occasion prefix rule `link_piece` uses today, so "Built to Spill Fall 2026 Tour" links its act). An act awaiting an editor's review (`needs_review`) has no page, so its name stays plain. The play buttons are the listing's (`event_artist_previews`), Bandcamp's included. The venue line gives the venue's neighborhood, when known, beside its town, as the listing does. The shared card styles move from `band.scss` into a `_card.scss` partial that both pages import.
*Alternative:* a plain page without the card. Rejected: the card is the site's one container, and an event and an act are both "records" in the record-store bin (DESIGN.md).

### 5. Ticket and venue links are compared normalized
"Same URL" means equal after trimming whitespace, lowercasing the scheme and host, and dropping a trailing slash and a `utm_*` query. Then one "Tickets ↗" link shows; otherwise "Tickets ↗" and "Venue's page ↗". Both open in a new tab with `rel="noopener"`.

### 6. Search engines and the sitemap
The site can be shared now, so an upcoming event's page carries no `noindex` and has a canonical link to itself. A past event's page asks not to be indexed (`noindex`), so search results don't send people to shows that are over. Event pages stay out of the sitemap in this change; adding them is `improve-sitemap`'s work.

## Risks / Trade-offs

- [The billing misreads a title, and the headline shows a fragment] → `billing` falls back to the full title when the names it finds cover less than the title's first word, and the title line keeps the original wording visible. Tests cover the listings seen on 2026-10-30 (Nekrogoblikon, Disko Lunatics, Dev Lemons, Bluegrass Jam).
- [Visitors used to the headline taking them to the venue's site] → the tix badge stays one click to tickets, and the event page's links are the first thing under the acts.
- [Telegram and other bots that followed the redirect] → they now get a real page with the same metadata, which is what previews need.
- [About 5,200 production listings must be re-rendered] → `resave_all_events` after deploy, as for `add-band-pages`. Until it runs, old rows still work (they link out as before).
- [Search engines index pages for events outside New England, which the listings hide] → those pages still answer, as a shared link to one should (`limit-listings-to-new-england` keeps an event's own link working), but nothing on the site links to them.

## Migration Plan

1. Build on `add-event-pages` (`add-band-pages`, whose spec is modified here, is archived).
2. Deploy; then run `resave_all_events` on Render (a one-off job, with approval) so every listing is re-rendered.
3. Rollback: revert the deploy and run `resave_all_events` again; no data changes.
