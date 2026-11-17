# Design

## Context

See `proposal.md` for why. What shapes the approach:

- **The styles today** are 17 SCSS files under `core/static/core/scss/`, compiled by `django-sass-processor` (`compilescss` in `bin/build.sh` and the `Dockerfile`), loaded by one `{% sass_src 'scss/core.scss' %}` in `core/templates/core/base.html`. Colours and sizes are literals; `DESIGN.md` documents them after the fact.
- **The build has no Node.js.** Render runs `bin/build.sh` on a Python image, and the `Dockerfile` starts from `python:3.12.1`.
- **Listing rows are stored HTML.** `Event.save()` renders `core/event.html` into `Event.baked_html_template`, and `Venue.save()` re-renders every one of its events. A new row template shows nowhere until events are re-rendered.
- **Maps** are MapLibre with Protomaps tiles (`core/templates/map/map.html`), drawn only when `protomaps_api_key` is set and opened by a "SHOW MAP" link. The venue page draws no map, because Google's Places terms ask for Places results to be shown on a Google map; that question is still the owner's.
- **The designs** are seven 1440px artboards in one Paper file. Six share one header; "Home (alternative)" has its own. The file's token list is Tailwind v4's default shape (greys, a blue scale at hue 258, type sizes, weights, tracking, leading, breakpoints, containers, radii). The artboards also use values that aren't in that list: the yellow `#FFEF3B`, Inter Tight, Geist Mono and the map's colours. The list names Inter and DM Mono, but no artboard uses them.
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
| `--color-surface` | `var(--color-gray-100)` | the search bar, the "Want to play here?" and "Is this you?" boxes, Discover's ground |
| `--color-ink` | `#000000` | headings, names, filled buttons |
| `--color-icon` | `#171717` | line icons |
| `--color-body` | `var(--color-gray-700)` | detail lines |
| `--color-quiet` | `var(--color-gray-600)` | secondary lines, placeholders, breadcrumb slashes |
| `--color-rule` | `var(--color-gray-200)` | row rules, the header's bottom edge |
| `--color-control` | `var(--color-gray-500)` | unchecked radio and checkbox borders |
| `--color-link` | `var(--color-blue-600)` | links, checked controls |
| `--color-accent` | `#FFEF3B` | the search button, tags ("Tonight", "Open booking", ticket dates), the next-show band, the chosen map pin, the primary Discover button |
| `--color-on-accent` | `#000000` | type on the accent |
| `--color-map-ground` | `#EEF1EE` | the map panel behind its tiles |
| `--color-map-water` | `#BFDDE3` | the map's water |
| `--color-map-park` | `#D9E8D6` | the map's parks |
| `--color-map-pin` | `#171717` | map pins |
| `--color-map-you` | `#1F35FF` | the visitor's location dot |
| `--font-display` | `"Inter Tight", system-ui, sans-serif` | the name, headings, row titles, poster tiles |
| `--font-sans` | `system-ui, sans-serif` | everything else |
| `--font-mono` | `"Geist Mono", ui-monospace, monospace` | small caps labels ("NOV 16 · O'BRIEN'S", "MON NOV", "ACT 12 OF 86") |
| `--radius-tile` | `var(--radius-lg)` (8px) | poster tiles, map callouts |
| `--radius-box` | `var(--radius-xl)` (12px) | boxes and the venue map |
| `--radius-control` | `var(--radius-sm)` (4px) | checkboxes |
| `--radius-pill` | `9999px` | the search bar, buttons, genre pills, radios |

The artboards' own named sizes become roles too, so headings don't drift: page heading 40px/48px at -0.025em; the venue's and band's name 72px to 96px, clamped for phones; row title 22px/28px at -0.015em; section heading 24px/28px at -0.02em; body 16px/24px; detail 15px/22px; small 14px/20px; label 11px/14px at 0.06em.

Where the Paper file's token list and its artboards disagree (Inter and DM Mono against Inter Tight, system sans and Geist Mono), the artboards win, because they're what was drawn. The same goes for layout sizes: 40px page gutters, a 200px filter rail, a 440px map panel, a 208px by 117px poster tile.

- *Instead of roles only:* the scales cost nothing and keep Paper's export classes (`text-gray-700`) meaningful while a screen is being built. The built stylesheet contains only the classes templates use.
- *Instead of scales only:* then "make the accent orange" is a search across every template.

### 3. Templates use roles; a test keeps it that way

A test scans `core/templates/` (not `admin/` or `email/`) and `core/static/core/css/` other than `tokens.css`, and fails on a hex, `rgb()`, `hsl()` or `oklch()` colour, a Tailwind arbitrary colour (`bg-[#…]`), a scale colour class (`text-gray-700`, `bg-blue-600`) or a `font-[…]` class. Inline SVG uses `currentColor` or a `var(--color-…)`. This is the "easy customization" the request asks for, held by a test and not by habit.

### 4. Parts are Django includes, not `@apply` classes

Repeated things are template includes with their utility classes inside: `core/parts/header.html`, `breadcrumbs.html`, `filter_rail.html`, `map_panel.html`, `show_row.html`, `date_block.html`, `poster_tile.html`, `tag.html`, `pill.html`, `button.html`. `site.css` holds only what utilities can't say: the `@import` of Tailwind and the tokens, `@font-face`, base element styles for editors' rich text (`.prose-site`), and the overrides for the two vendored widgets (accessible-autocomplete's menu and MapLibre's controls).

- *Instead of `@apply` component classes:* Tailwind's own advice is against it, and it rebuilds the stylesheet-per-component sprawl this change removes.

### 5. Poster tiles are drawn from text

The artboards' tiles hold no image: the headliner's name in Inter Tight capitals over a mono line (date and venue), on one of four grounds (ink, accent, link blue, light grey; and accent type on ink). The ground is chosen from the event's ID modulo the grounds, so a show keeps its tile between visits and a page of rows varies. The band page's large tile says "Photo goes here when the act has one" in the design; on the site it shows the act's photo when it has a free-licensed one (the existing rule) and the text tile otherwise, without that sentence.

### 6. The listing row is rebuilt once, and events are re-rendered at deploy

`core/event.html` becomes the new row (tile, title, openers, time, venue line, price, save icon), keeping every hook the scripts and tests use: the save toggle, the action icons, the play buttons and the row's anchor. Because rows are stored, the deploy runs `resave_all_events` once, which re-renders every stored row. The home page's rows and the venue page's bill are different shapes in the design; the bill is not stored HTML, so only the listing row needs the re-render.

### 7. Maps: same map, new frame

The home and venues listings put the existing MapLibre map in a sticky panel at the right, 440px wide, open by default from 1024px up and behind a "Map" button below that. It is drawn only when a Protomaps key is set; without one the list takes the full width. Pins, callouts and the location dot take the token colours. Nothing about which coordinates are pinned changes, so the open Places question is neither better nor worse. The venue page's small map is left out, and "Directions" links out as "Map" does today.

### 8. The header's location is the existing location form

"Medford, MA" in the search bar is the visitor's saved location (`core/location.py`), and clicking it opens the existing form and its suggestions in a popover. With no location set it reads "Set your location". The listing's heading follows: "Live music near Medford, MA" with a location, "Live music in Greater Boston" with only an area filter, "Live music across New England" with neither.

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

- Home: date shortcuts (Tonight, Tomorrow, This weekend, Pick a date); a distance radius (5, 25, 50 miles); price (Free, Ticketed); "For musicians" (Open booking, Open mics); "9 more shows tonight" paging within a day.
- Venues: a distance radius; "Kind of room"; "Has an open mic"; "47 rooms take open bookings" as a live count is drawn (it's a count of what's listed), but sorting other than A–Z is not.
- Bands: "Playing soon" and "Playing near me"; Bands or Solo artists; New England or Touring.
- Band page: genre pills are drawn from the genres the act has; the per-show "From $25" needs a parsed price, so the stored price text is shown as it is.
- Venue page: the fact table's "Size", "Ages" and "Access" rows are drawn only when the venue has them.

## Risks / Trade-offs

- **A page is missed and ships unstyled** → a test requests every public URL pattern and fails if the response still loads an SCSS stylesheet or lacks the new header.
- **Tests tied to old markup break in bulk** → each page's tests move in the same commit as its template; behaviour tests keep their hooks (`data-` attributes, IDs), which the new templates preserve.
- **Stored rows show the old look after deploy** → the re-render is a deploy step, checked by a test that a re-rendered row carries the new markup; a row not yet re-rendered still reads correctly, only plainer.
- **The build can't fetch Tailwind's program** (network or a moved release) → the build fails loudly before deploy, not at runtime; the version is pinned.
- **Density drops.** The old listing shows far more shows per screen than the new rows with tiles. This is the design's choice; the month archive pages keep a compact row (no tile) so a whole month stays scannable.
- **Phone layouts are undrawn** → built to the rules in the proposal and shown to the owner as screenshots before G4.
- **Editors' rich text** (static pages, pre- and post-calendar messages) was styled by element selectors that Tailwind's reset removes → `.prose-site` restores headings, lists and links for those blocks.
- **`DESIGN.md` and the `impeccable` tooling** describe the old system → rewritten in this change, so later design work doesn't steer back to plum and lavender.

## Migration Plan

1. Merge only when every page has moved and the suite passes.
2. Deploy: `bin/build.sh` builds the stylesheet, then `collectstatic`.
3. Run `resave_all_events` once.
4. Rollback: revert the merge and redeploy; then run `resave_all_events` again so stored rows return to the old markup. No data changes either way.

## Open Questions

- **Which home page.** This plan builds the Eventbrite-style home, because its header is the one the other five screens share. If the alternative home (week strip, month calendar in the rail) is the wanted one, the header, the home task group and the `site-layout` spec change. To settle at G2.
- **The venue page's map.** Left out here. If the owner settles the Places map term, it's a small follow-up.
