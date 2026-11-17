# Design

## Context

See `proposal.md` for why. What shapes the approach:

- **The styles today** are 17 SCSS files under `core/static/core/scss/`, compiled by `django-sass-processor` (`compilescss` in `bin/build.sh` and the `Dockerfile`), loaded by one `{% sass_src 'scss/core.scss' %}` in `core/templates/core/base.html`. Colours and sizes are literals; `DESIGN.md` documents them after the fact.
- **The build has no Node.js.** Render runs `bin/build.sh` on a Python image, and the `Dockerfile` starts from `python:3.12.1`.
- **Listing rows are stored HTML.** `Event.save()` renders `core/event.html` into `Event.baked_html_template`, and `Venue.save()` re-renders every one of its events. A new row template shows nowhere until events are re-rendered.
- **Maps** are MapLibre with Protomaps tiles (`core/templates/map/map.html`), drawn only when `protomaps_api_key` is set and opened by a "SHOW MAP" link. The venue page draws no map, because Google's Places terms ask for Places results to be shown on a Google map; that question is still the owner's.
- **The designs** are one Paper file, "StageHopper", of 1440px artboards. The home page is its first artboard, "Home (alternative)" (the owner's choice, 16 November 2026); "Home (Eventbrite-style)" is set aside. Five artboards were drawn for this change in the home page's style: "Home — map shown", "Event — page", "Search — suggestions as you type", "Search — results" and "Saved shows". Five earlier artboards (venues listing, venue page, bands listing, band page, Discover) carry the Eventbrite-style header and slightly different greys and blue. The file's token list is Tailwind v4's default shape (greys, a blue scale at hue 258, type sizes, weights, tracking, leading, breakpoints, containers, radii), and the artboards also use values outside it: the yellow `#FFEF3B`, the link blue `#1F35FF`, Inter Tight, Geist Mono and the map's colours. The list names Inter and DM Mono, but no artboard uses them.
- **Browser tests** (Playwright) load real pages, so they need the built stylesheet, as they need `compilescss` today.

## Goals / Non-Goals

**Goals:**
- Every public page in the new look, built from the artboards' exact values (read with Paper's code export, never from screenshots).
- One file to edit to restyle the site.
- No Node.js in the build, and no request to another site for fonts or styles.
- Every existing behaviour and test scenario still passing.

**Non-Goals:**
- New filters, sorts or data (listed under "Follow-ups" below).
- A map on the venue page, or any change to which coordinates a map may show.
- The admin's look.
- Dark mode. The tokens make it possible later; nothing here draws it.
- The email digest's HTML, which mail programs render with their own rules; it keeps its inline styles and takes only the new colours.

## Decisions

### 1. Tailwind v4, run by its standalone program through `django-tailwind-cli`

Tailwind v4 reads its theme from CSS (`@theme`), which is what makes a single token file possible, and Paper exports its tokens in exactly that form. Its standalone program is one binary with no Node.js. `django-tailwind-cli` fetches a pinned version of it and adds `manage.py tailwind build` and `tailwind watch`.

- *Instead of the CDN script:* it restyles in the browser on every page view, needs a request to another site, and Tailwind says not to use it in production.
- *Instead of Node.js and npm:* a second toolchain on Render and in the `Dockerfile` for one build step.
- *Instead of keeping SCSS with CSS variables:* it would give the token file but not the utility classes the Paper export is written in, so every artboard would be translated by hand twice.

The pinned Tailwind version is set in settings (`TAILWIND_CLI_VERSION`), so a build never picks up a new release by itself. Confirm the package's current setting names against its documentation when installing; they've changed between releases.

### 2. Two layers of tokens in one file

`core/static/core/css/tokens.css` is one `@theme` block in two parts.

**The scales,** copied from the Paper file (`get_tokens`, Tailwind format): `--color-gray-50…950`, `--color-blue-50…950`, `--text-xs…9xl`, `--font-weight-*`, `--tracking-*`, `--leading-*`, `--breakpoint-*`, `--container-*`, `--radius-xs…4xl`.

**The roles,** which are what templates use:

| Role | Value | Used for |
| --- | --- | --- |
| `--color-ground` | `#FFFFFF` | the page |
| `--color-surface` | `#F4F4F4` | the search box, the "Want to play here?" and "Is this you?" boxes, Discover's ground |
| `--color-ink` | `#000000` | headings, names, filled buttons, heavy rules, icons |
| `--color-quiet` | `#555555` | secondary lines, small caps labels, placeholders, breadcrumb slashes |
| `--color-faint` | `#888888` | days already past in the month calendar |
| `--color-rule` | `#E6E6E6` | row rules, the header's bottom edge, outline chips |
| `--color-link` | `#1F35FF` | links, "Change", checked controls, the visitor's location dot |
| `--color-accent` | `#FFEF3B` | ticket prices, tags ("Tonight", a next show's date), today in the week strip and month calendar, the saved count, the chosen suggestion, the chosen map pin, the next-show band |
| `--color-on-accent` | `#000000` | type on the accent |
| `--color-map-ground` | `#EEF1EE` | the map behind its tiles |
| `--color-map-water` | `#BFDDE3` | the map's water |
| `--color-map-park` | `#D9E8D6` | the map's parks |
| `--color-map-pin` | `#000000` | map pins |
| `--font-display` | `"Inter Tight", system-ui, sans-serif` | the name, headings, show names, date numbers |
| `--font-sans` | `system-ui, sans-serif` | everything else |
| `--font-mono` | `"Geist Mono", ui-monospace, monospace` | times, small caps labels ("MONDAY, NOVEMBER 16", "TIX $15", "BAND") |
| `--radius-box` | `var(--radius-lg)` (8px) | the search box, the location field, the map, menus, callouts |
| `--radius-chip` | `var(--radius-md)` (6px) | today in the month calendar |
| `--radius-pill` | `9999px` | buttons, play buttons, genre pills, the saved count |

Tags and ticket prices are square, with no radius.

The artboards' own named sizes become roles too, so headings don't drift: display 96px/92px at -0.045em and weight 800 ("Tonight", a show's or venue's name, clamped down for phones); section heading 28px/32px at -0.02em; show name 22px/28px at -0.015em, weight 800; body 16px/24px; detail 15px/22px; small 14px/20px; time 14px mono; label 12px to 13px mono at 0.08em, capitals.

Where sources disagree, the home page wins, because it's the chosen screen: its link blue and greys over the earlier artboards' `blue-600` and grey scale steps, and the artboards' fonts over the token list's Inter and DM Mono. Layout sizes come from it too: 56px page gutters, a 248px rail, a 64px gap, and a show row's columns (84px time, 280px venue, 128px price and bookmark). Because every template uses roles, bringing the five earlier screens onto these values costs nothing beyond building them.

- *Instead of roles only:* the scales cost nothing and keep Paper's export classes (`text-gray-700`) meaningful while a screen is being built. The built stylesheet contains only the classes templates use.
- *Instead of scales only:* then "make the accent orange" is a search across every template.

### 3. Templates use roles; a test keeps it that way

A test scans `core/templates/` (not `admin/` or `email/`) and `core/static/core/css/` other than `tokens.css`, and fails on a hex, `rgb()`, `hsl()` or `oklch()` colour, a Tailwind arbitrary colour (`bg-[#…]`), a scale colour class (`text-gray-700`, `bg-blue-600`) or a `font-[…]` class. Inline SVG uses `currentColor` or a `var(--color-…)`. This is the "easy customization" the request asks for, held by a test and not by habit.

### 4. Parts are Django includes, not `@apply` classes

Repeated things are template includes with their utility classes inside: `core/parts/header.html`, `breadcrumbs.html`, `rail.html`, `page_head.html` (small caps line, large heading, count and map link), `week_strip.html`, `day_map.html`, `show_row.html`, `date_block.html`, `fact_table.html`, `tag.html`, `pill.html`, `button.html`. `site.css` holds only what utilities can't say: the `@import` of Tailwind and the tokens, `@font-face`, base element styles for editors' rich text (`.prose-site`), and the overrides for the two vendored widgets (accessible-autocomplete's menu and MapLibre's controls).

- *Instead of `@apply` component classes:* Tailwind's own advice is against it, and it rebuilds the stylesheet-per-component sprawl this change removes.

### 5. One header and one row, from the home page

The five earlier artboards draw a different header (the location inside a rounded search bar, icons over the links) and, on the venues listing, an always-open map panel. Building two headers would make the site read as two sites, so every page takes the home page's header, the location moves to the rail on pages that have one, and the venues listing gets the same "Show on map" link as the home page. Nothing draws a poster tile: the Eventbrite-style rows that needed one are set aside.

- *Instead of the earlier header everywhere:* the home page was chosen after those screens were drawn, and its header is the simpler one (no icons, no second field).

### 6. The listing row is rebuilt once, and events are re-rendered at deploy

`core/event.html` becomes the new row (time, name and openers, venue line, price, save bookmark), keeping every hook the scripts and tests use: the save toggle, the play buttons and the row's anchor. The drawn row shows only the bookmark, at its right end. The row's four link icons (calendar download, Google Calendar, map, share) and its play buttons, which the drawing leaves out, are kept: they sit on a second, quieter line under the show's text, as they wrap today, so no listing loses an action. On the event's page the same four actions are drawn as text links beside the buttons. Because rows are stored, the deploy runs `resave_all_events` once, which re-renders every stored row. The same row is used on Saved shows and, with a date in place of the bare time, for upcoming shows in search results; the venue page's bill and the band page's show list use the date block instead and are not stored HTML.

### 7. Maps: the same day map, opened by "Show on map"

Today each day on the listing has a "SHOW MAP" link that opens a MapLibre map of that day's shows, and Saved shows has one map of everything saved. Both stay, in the new look: the link sits beside the day's count and reads "Show on map", then "Hide map"; the map opens above the day's rows at the list's width, 380px tall, with a line saying how many of the day's listed shows are pinned; a chosen pin's callout names the show, venue and time and links to the show. Pins, the callout and the location dot take the token colours. The map still loads nothing until opened, and is offered only when a Protomaps key is set. Which coordinates are pinned is unchanged, so the open Places question is neither better nor worse. The venue page's small map is left out, and "Directions" links out as "Map" does today.

The count line needs the number of the day's listed shows and the number pinned, which the map script already has when it builds the pins.

### 8. The rail's location is the existing location form

"Medford, MA" with "Change" at the top of the home page's rail is the visitor's saved location (`core/location.py`); "Change" opens the existing form and its suggestions in place. With no location it reads "Set your location". The count line follows: "14 shows near Medford" with a location, "in Greater Boston" with only an area filter, "across New England" with neither. The drawn "within 25 miles" needs a distance filter the site doesn't have (see Follow-ups).

The week strip's counts come from the events the view has already grouped by day (`grouped_events_as_list`), so they cost no extra query and follow the filters.

### 9. Pages move one at a time, on the branch, behind one base template

`base.html` is replaced first, loading the Tailwind stylesheet. Each page then moves in its own commit, with its tests. Until a page moves it would render unstyled, so the branch is not deployable midway; it merges only when every page has moved and the SCSS is gone. This is why the work is one change and not one per screen.

- *Instead of a setting that switches looks:* two full sets of templates to keep working, for a site with one owner who has already chosen.

### 10. Tests and external services

- **Tailwind's program** is fetched at build time only. Tests never fetch it: the test runner builds the stylesheet once if the binary is already there and the built file is older than its sources; when the binary is missing, browser tests are skipped with a message naming the command to run, and every other test runs.
- **Fonts** are files in `core/static/core/fonts/`, so no test or page requests a font host.
- **Map tiles (Protomaps)** are mocked in browser tests as the existing map tests do, by routing tile requests to a local stub; no new map behaviour needs the network.
- **Paper** is read by hand during implementation and is not a dependency of the code or the tests. Each screen's task records the artboard it was built from.
- No other external service is touched by this change.

## Follow-ups (each its own proposal)

Controls the artboards draw that the site can't do today, left out of this change:

- Home: the distance chips (5, 25, 50 miles, Any) and "within 25 miles" in the count line; "9 more shows tonight" (showing part of a day).
- Venues: a distance radius; "Kind of room"; "Has an open mic".
- Bands: "Playing soon" and "Playing near me"; Bands or Solo artists; New England or Touring.
- Band page and event page: "From $25" needs a parsed price, so the stored price text is shown as it is. Rows show "TIX" with the price text when it's short, and "TIX" alone otherwise.
- Event page: the drawn "Doors 6:30" is not built, as events have no doors time; "Next at <venue>" lists the venue's next three approved shows, which the venue page already queries.
- Search results: "Show upcoming shows on map" arrives with `add-search-results-map`.
- Venue page: the fact table's "Size", "Ages" and "Access" rows are drawn only when the venue has them.

## Risks / Trade-offs

- **A page is missed and ships unstyled** → a test requests every public URL pattern and fails if the response still loads an SCSS stylesheet or lacks the new header.
- **Tests tied to old markup break in bulk** → each page's tests move in the same commit as its template; behaviour tests keep their hooks (`data-` attributes, IDs), which the new templates preserve.
- **Stored rows show the old look after deploy** → the re-render is a deploy step, checked by a test that a re-rendered row carries the new markup; a row not yet re-rendered still reads correctly, only plainer.
- **The build can't fetch Tailwind's program** (network or a moved release) → the build fails loudly before deploy, not at runtime; the version is pinned.
- **Density drops a little.** The new row is taller than the old one (about 72px against 45px). This is the design's choice; the month archive pages use the same row.
- **The row is busier than the drawing.** Keeping the link icons and play buttons under each show adds a line the artboard doesn't have. Dropping them from listings would be a behaviour change (`event-action-icons`), so it's left for the owner to ask for.
- **Phone layouts are undrawn** → built to the rules in the proposal and shown to the owner as screenshots before G4.
- **Editors' rich text** (static pages, pre- and post-calendar messages) was styled by element selectors that Tailwind's reset removes → `.prose-site` restores headings, lists and links for those blocks.
- **`DESIGN.md` and the `impeccable` tooling** describe the old system → rewritten in this change, so later design work doesn't steer back to plum and lavender.

## Migration Plan

1. Merge only when every page has moved and the suite passes.
2. Deploy: `bin/build.sh` builds the stylesheet, then `collectstatic`.
3. Run `resave_all_events` once.
4. Rollback: revert the merge and redeploy; then run `resave_all_events` again so stored rows return to the old markup. No data changes either way.

## Open Questions

- **One header.** This plan puts the home page's header on every page, including the five screens drawn with the other one (decision 5). To confirm at G2.
- **The venue page's map.** Left out here. If the owner settles the Places map term, it's a small follow-up.
