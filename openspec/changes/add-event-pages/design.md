## Context

- `/event/<id>` is `core/views/event_redirect.py`: it renders `core/empty.html`, a page of share-preview metadata that redirects to `/<month>/#event-<id>` (one second late for Telegram's bot). The share icon (`core/event_actions.py`), calendar feeds (`core/calendar_feeds.py`, via the `event_redirect` URL name) and the band page's show rows (`core/templates/core/band.html`) all link there.
- A listing row is `core/templates/core/event.html`, rendered once and stored in `Event.baked_html_template` by `bake_event_html` (`core/utils_event_caching.py`). Its icon row is a placeholder filled per page (`event-action-icons`). Since `add-band-pages`, `listing_parts` (`core/event_performers.py`) splits the title and artists into pieces and links the performers' names, and `rebake` re-renders an event when its performers change.
- `event_artist_names` (`core/artist_names.py`) already reads an event's acts in order: the title's names first, then the artists', without repeats, with kinds of night, tours and notes dropped.
- The day map (`core/templates/map/map.html`) reads each row's `data-` attributes and clones rows into its popups.
- The band page (`core/templates/core/band.html`, `core/static/core/scss/band.scss`) defines the index card: the plum tab, card stock, the lavender strip with the icon row, ruled show rows.

## Goals / Non-Goals

**Goals:**
- One meaning per link in a listing, with the band pages one click away on the event page.
- The listing's stored HTML stops depending on which performers are linked, so linking or unlinking an act no longer re-renders listings.

**Non-Goals:**
- A readable slug in the event URL (`/event/123` stays; a slug can be added later without changing these specs).
- Venue pages. The event page shows the venue's name and facts, not a link to a venue page that doesn't exist yet.
- Changing which events are approved, or the event admin.

## Decisions

### 1. The redirect view becomes the page, at the same URL
`/event/<id>` renders `core/event_page.html` for an approved event and answers 404 otherwise (`Event.objects`, approved only). Its share metadata (`get_meta`, title "<time> @ <venue> - <acts>") moves into the page's head unchanged, so previews look the same. The URL name changes from `event_redirect` to `event_page`; the three callers are updated. `core/empty.html` and the Telegram delay go with the redirect.
*Alternative:* a new `/events/<id>` with the old address redirecting to it. Rejected: every link that exists already points at `/event/<id>`, and two addresses for one page splits share counts for nothing.

### 2. One function reads the billing: title line, headliner, openers
A new `billing(event)` in `core/artist_names.py` returns `(title_line, headliner, openers)` from `event_artist_names(event)`. The headliner is the first name, the openers the rest. The title line is the event's title when, after removing the presenter prefix and every act name and separator from it, words remain that aren't joiners ("with", "and", "&", "presents", "special guests") or punctuation; otherwise it's empty. With no act names at all, the headliner is the title (or the artists text), so a kind of night still has a headline. Both the listing and the event page use it, so they always agree.
*Alternative:* keep `listing_parts`, which preserves the source text's exact pieces and separators. Rejected for the listing: it can't rank acts, and it prints a name the title and artists both give twice. It stays for nothing else and is removed with its tests.

### 3. The listing is still stored HTML, and stops naming performers
`event.html` renders: an optional `.event-title-line` (small, quiet), then the headline as `<a class="event-headline" href="/event/<id>">` holding the headliner in a bold, larger `<b>`, then `with <openers>` in regular weight, then price, venue, age policy and town, description and access notes as now. The `hyperlink` no longer wraps anything and the `info ↗` link is removed. Because the row no longer depends on performers, `rebake` calls on performer changes and the delete signals (`CoreConfig.ready`) are removed; the row still re-renders on event and venue saves, as before `add-band-pages`.
*Alternative:* render rows per request. Rejected: the stored HTML is what keeps the homepage fast (about 2,000 rows), and nothing on the row now changes between saves.

### 4. The event page reuses the band page's card
`event_page.html` extends the base template and draws one card: the date and time as the plum tab (display type, "Thu Oct 30 · 7:00 p.m."), the title line, the headliner (larger, linked when a performer) and openers (linked when performers) in the lavender strip with the icon row, then a field list (Venue, Price, Ages, Access, Links) and the description, then the play buttons. Performer links come from `event.performers` matched to the billing names by normalized name (with the occasion prefix rule `link_piece` uses today, so "Built to Spill Fall 2026 Tour" links its act). The shared card styles move from `band.scss` into a `_card.scss` partial that both pages import.
*Alternative:* a plain page without the card. Rejected: the card is the site's one container, and an event and an act are both "records" in the record-store bin (DESIGN.md).

### 5. Ticket and venue links are compared normalized
"Same URL" means equal after trimming whitespace, lowercasing the scheme and host, and dropping a trailing slash and a `utm_*` query. Then one "Tickets ↗" link shows; otherwise "Tickets ↗" and "Venue's page ↗". Both open in a new tab with `rel="noopener"`.

### 6. `noindex` and the sitemap
The page always carries `<meta name="robots" content="noindex">` in this change, and event pages stay out of the sitemap: the site is unshared (PRODUCT.md), and event pages expire with their shows. Indexing them is a decision for when the site is shared, along with the sitemap work in `improve-sitemap`.

## Risks / Trade-offs

- [The billing misreads a title, and the headline shows a fragment] → `billing` falls back to the full title when the names it finds cover less than the title's first word, and the title line keeps the original wording visible. Tests cover the listings seen on 2026-10-30 (Nekrogoblikon, Disko Lunatics, Dev Lemons, Bluegrass Jam).
- [Visitors used to the headline taking them to the venue's site] → the tix badge stays one click to tickets, and the event page's links are the first thing under the acts.
- [Telegram and other bots that followed the redirect] → they now get a real page with the same metadata, which is what previews need.
- [About 3,300 production listings must be re-rendered] → `resave_all_events` after deploy, as for `add-band-pages`. Until it runs, old rows still work (they link out as before).

## Migration Plan

1. Archive `add-band-pages` (its spec is modified here), then build on `add-event-pages`.
2. Deploy; then run `resave_all_events` on Render (a one-off job, with approval) so every listing is re-rendered.
3. Rollback: revert the deploy and run `resave_all_events` again; no data changes.
