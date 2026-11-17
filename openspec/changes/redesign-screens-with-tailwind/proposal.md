# Proposal

## Why

The site still wears the look it inherited from nyc noise: one 42em column on grey paper, set in hand-written SCSS (about 2,800 lines across 17 files) with colours and sizes repeated as literals. Nate has drawn a new look for StageHopper in Paper (the "StageHopper" file of 1440px artboards), and it can't be reached by adjusting the old stylesheets. It needs a wide layout, a new header, a rail beside each list and a new show row. Rebuilding on Tailwind CSS, with every colour, font, size and radius read from one token file, makes this redesign possible and the next restyle a one-file edit.

## What Changes

- **BREAKING (visual): every public page gets the new look.** White ground, black ink, one yellow accent (`#FFEF3B`), blue underlined links, Inter Tight headings, system sans body text, Geist Mono small caps labels. The grey paper, plum tabs and lavender strips go.
- **Tailwind CSS v4 replaces SCSS.** The stylesheet is built by Tailwind's standalone program (no Node.js), at build time, as `compilescss` is today. `django-sass-processor`, `libsass` and `core/static/core/scss/` are removed once the last page has moved.
- **One token file.** `core/static/core/css/tokens.css` holds a Tailwind `@theme` block: Paper's own token scales (greys, blues, type sizes, radii, breakpoints, containers) and a short list of named roles on top of them (`accent`, `ink`, `link`, `quiet`, `rule`, `surface`, the map's colours, the three font families). Templates use the roles only, never a literal colour or font, so a restyle is an edit to this file. A test fails when a template or stylesheet uses a literal colour.
- **The home page is the first artboard, "StageHopper — Home (alternative)"** (the owner's decision, 16 November 2026). The Eventbrite-style home is set aside: its rows need an image for every show, and the site has none.
  - *The page:* a rail at the left (the visitor's location, the area filters, the month calendar, the calendar subscription); at the right the date in small caps over a large "Tonight", the count of shows, a week strip of the next seven days with each day's count, then each show as a row: time, name and openers, venue with its place, distance and ages, the ticket price on yellow or "FREE", and the save bookmark. The row's calendar, map and share icons and its play buttons, which the drawing leaves out, stay on a second line under each show.
  - *Days still run down the page* as they do today. Each later day opens with its own date heading, and the week strip jumps to a day. The "9 more shows tonight" link in the drawing is not built: every show of a day is listed.
- **"Show on map" shows the listed shows on a map** (artboard "Home — map shown"). The link beside a day's count opens a map above that day's rows, with a pin for each of that day's listed shows at a located venue, a line saying how many are on the map ("12 of 14 shows on the map"), and a callout naming the show at a chosen pin with a link to it. The link then reads "Hide map". This is today's day map and "SHOW MAP" link in the new look, drawn only when a Protomaps key is set.
- **One header on every page, the home page's:** the name; the search box; and "Bands & artists", "Venues", "Submit a show" and "Saved" with its count on a yellow badge. The burger menu and the tagline under the name go; the tagline moves to the footer. The five inner artboards drawn earlier (venues listing, venue page, bands listing, band page, Discover) show the Eventbrite-style header, with the location inside a rounded search bar and icons over the links; they are built with their own content under the home page's header, and the location lives in the rail where a page has one.
- **Four pages drawn for this change,** in the same Paper file, in the home page's style:
  - *Event page* ("Event — page"): breadcrumbs through the venue; the date and time in small caps; the headliner large, with "Tonight" on yellow when it is; the openers as links; a bar of "Tickets", "Save" and "Venue's page" with the calendar and share links; "Listen first" with each act's play buttons; "About this show"; and at the right a fact table (venue, distance and directions, price, ages, access) and "Next at <venue>".
  - *Search suggestions* ("Search — suggestions as you type"): the suggestions the site gives today, in a menu under the search box: a label per group, each row with its kind in small caps, the name with the typed part marked, and its place or date; the chosen row on yellow; "See all results" at the foot.
  - *Search results* ("Search — results"): what was searched as the heading with the count; a "Jump to" rail; then a section per kind as today (bands and artists, venues, shows, past shows), the typed part marked in each name, upcoming shows as full rows with their date, past shows as plain quiet rows.
  - *Saved shows* ("Saved shows"): a rail with the location and how saving works; the heading with the count and "Show on map"; the saved shows grouped by day, as listing rows.
- **The other screens, rebuilt from their artboards** under the shared header: venues listing, venue page, bands listing, band page and Discover bands. The venues listing's always-open map panel becomes the same "Show on map" link as the home page's.
- **Breadcrumbs** on every page below the home page (Home / Venues / O'Brien's / Brookelen, Nov 16).
- **Pages with no artboard are restyled with the same header, tokens and parts,** with their content and behaviour unchanged: the month archive pages, submit a show, the digest pages, the location form, privacy, terms and editors' static pages. The admin is untouched.
- **Phones and tablets.** The artboards are desktop only. Below 1024px the rail folds into a "Filters" drawer; below 640px the header's links fold behind a "Menu" button and a show row stacks (time and name, then venue, then price and bookmark). These layouts are this proposal's, not the designer's.
- **Looks only: a control is drawn only when the site can already do it.** The home rail's distance chips (5, 25, 50 miles, Any) are left out, because the site sorts and labels by distance but can't filter by it; the count line reads "14 shows near Medford" in place of "within 25 miles of Medford". The other artboards' undrawn-behaviour filters (kind of room, "Has an open mic", acts playing soon, bands or solo artists, New England or touring) are left out the same way. Each is listed in `design.md` as a follow-up proposal.
- **The venue page's small map is left out,** as the venue page's spec says no map is drawn there, until the owner settles the Google Places map term. Which coordinates any map may show is unchanged.
- **`DESIGN.md` is rewritten** to describe the new system, and `PRODUCT.md`'s notes on the look are brought into line.

## Capabilities

### New Capabilities
- `design-tokens`: the one token file every page's colours, fonts, sizes and radii come from, and the rule that templates and stylesheets use its named roles only.
- `site-layout`: what every page shares: the header (name, search box, the four links), breadcrumbs, the footer with the tagline and credits, the rail beside a list, the show row, the week strip, and how they fold on phones.

### Modified Capabilities
- `site-identity`: the tagline moves from the masthead to the footer.
- `act-index`: the search box moves into the header, beside the name; the index drops the 40-entry pages and the inverted "The" for one guide line per letter and names printed as they are.
- `event-action-icons`: the save bookmark moves from the icon row to the end of the show's row, after its price; the four link icons keep their own row.
- `saved-shows`: the header link reads "Saved" with the count on a yellow badge, in place of "Saved shows (3)"; the map's link reads "Show on map" and "Hide map".

The venue list, venue pages, the venue booking view, event pages, the event listing (with its day maps) and band discovery are described by specs that are still inside their own unarchived changes (`add-venue-list`, `add-venue-pages`, `add-event-pages`, `add-band-discovery-swipe`, `improve-band-discovery`), so this change can't carry deltas for them yet. Their behaviour is unchanged here; where one of them fixes a look (the venue page's plum tab, the event page's date tab), its wording is brought into line when that change is archived, before this one is (task group 1). `add-search-results-map` (not yet built) adds a map to search results; when it's built it uses this change's map part and link.

## Impact

- **Templates:** all of `core/templates/core/`, `core/templates/calendar/calendar.html` and `core/templates/map/map.html`. `core/templates/admin/` is untouched.
- **Styles:** `core/static/core/scss/` (17 files) removed; `core/static/core/css/tokens.css` and `core/static/core/css/site.css` added; the built file is not committed.
- **Scripts:** `saved_shows.js` (the count badge), `search-suggest.js` (the box's new place and the menu's rows), the map script in `map/map.html` (the link's wording, the count line, the callout), `discover.js`, `town_chips.js`, `location.js` and the inline burger script in `base.html`, where they find elements by class names that change.
- **Paper:** five artboards were added to the StageHopper file for this change ("Home — map shown", "Event — page", "Search — suggestions as you type", "Search — results", "Saved shows"); the first artboard is untouched.
- **Stored HTML:** each event's listing row is stored (`Event.baked_html_template`), so `resave_all_events` is run once at deploy.
- **Dependencies:** adds `django-tailwind-cli` (which fetches Tailwind's standalone program at build time); removes `django-sass-processor` and `libsass`. Adds self-hosted Inter Tight and Geist Mono font files (both SIL Open Font License); no font is loaded from another site.
- **Build and deploy:** `bin/build.sh` and the `Dockerfile` run the Tailwind build in place of `compilescss`; the test runner builds the stylesheet once before browser tests.
- **Tests:** tests that look for old class names or the masthead's wording change with the templates; new tests cover the token rule, the header, breadcrumbs, the week strip, the map link and the folded layouts.
- **No model, migration, URL or data change.** No new external service.
