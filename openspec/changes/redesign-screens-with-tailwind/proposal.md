# Proposal

## Why

The site still wears the look it inherited from nyc noise: one 42em column on grey paper, set in hand-written SCSS (about 2,800 lines across 17 files) with colours and sizes repeated as literals. Nate has drawn a new look for StageHopper in Paper (the "StageHopper" file: seven 1440px artboards), and it can't be reached by adjusting the old stylesheets. It needs a wide layout, a new header, a filter rail and a map panel. Rebuilding on Tailwind CSS, with every colour, font, size and radius read from one token file, makes this redesign possible and the next restyle a one-file edit.

## What Changes

- **BREAKING (visual): every public page gets the new look.** White ground, black ink, one yellow accent (`#FFEF3B`), blue underlined links, Inter Tight headings, system sans body text, Geist Mono small caps labels. The grey paper, plum tabs and lavender strips go.
- **Tailwind CSS v4 replaces SCSS.** The stylesheet is built by Tailwind's standalone program (no Node.js), at build time, as `compilescss` is today. `django-sass-processor`, `libsass` and `core/static/core/scss/` are removed once the last page has moved.
- **One token file.** `core/static/core/css/tokens.css` holds a Tailwind `@theme` block: Paper's own token scales (greys, blues, type sizes, radii, breakpoints, containers) and a short list of named roles on top of them (`accent`, `ink`, `link`, `quiet`, `rule`, `surface`, the map's colours, the three font families). Templates use the roles only, never a literal colour or font, so a restyle is an edit to this file. A test fails when a template or stylesheet uses a literal colour.
- **A new header on every page:** the name at the left; one rounded bar holding the search box and the visitor's location, with a yellow search button; then "Submit a show", "Saved" (with its count), "Venues" and "Bands", each an icon over a label. The burger menu and the tagline under the name go; the tagline moves to the footer.
- **Breadcrumbs** under the header on every page below the home page (Home / Venues / Allston / O'Brien's).
- **The seven designed screens, rebuilt from their artboards:**
  - *Home* ("StageHopper — Home (Eventbrite-style)"): a "Live music near <place>" heading, a filter rail at the left, show rows with a text poster tile, and a map panel at the right.
  - *Venues listing*: the same three-part layout, venue rows with their upcoming-show count and an "Open booking" tag.
  - *Venue page*: a large name, a fact line, genre pills, "Website" and "Directions" buttons, "Shows" and "For artists" tabs, "The bill" with big day numbers, and a fact table and a "Want to play here?" box at the right.
  - *Bands listing*: the letter rail across the page, a filter rail, and two columns of acts with their next show's date.
  - *Band page*: a poster tile, the name, genre pills, play buttons, a yellow "Next show" band, upcoming shows, members, links and "Is this you?".
  - *Discover bands*: the intro at the left, the card in the middle with "Skip" and "Add shows", and "Your picks" at the right.
- **The home page's second artboard ("Home (alternative)") is not built.** Its header differs from the one the other five screens share, so the Eventbrite-style home is taken as the chosen one. This is the first thing to confirm at review.
- **Pages with no artboard are restyled with the same header, tokens and parts,** with their content and behaviour unchanged: the event page, search results, Saved shows, the month archive pages, submit a show, the digest pages, the location form, privacy, terms and editors' static pages. The admin is untouched.
- **Phones and tablets.** The artboards are desktop only. Below 1024px the map panel closes behind a "Map" button and the filter rail folds into a "Filters" drawer; below 640px the header's labels drop to icons and the search bar takes its own row. These layouts are this proposal's, not the designer's.
- **Looks only: a control is drawn only when the site can already do it.** The artboards show filters the site doesn't have (date shortcuts, a distance radius, price, kind of room, "Has an open mic", acts playing soon, bands or solo artists, New England or touring). This change draws the filters that exist today (region, state, metro, towns and neighborhoods; the visitor's location; genre and "Takes open bookings" on venues; the letter rail) in the new rail, and leaves the rest out. Each missing filter is listed in `design.md` as a follow-up proposal.
- **Maps stay as they are underneath.** The home and venues map panels are the existing Protomaps map, opened by default at desktop width instead of by "SHOW MAP", and drawn only when a Protomaps key is set. The venue page's small map is left out, as the venue page's spec says no map is drawn there, until the owner settles the Google Places map term.
- **`DESIGN.md` is rewritten** to describe the new system, and `PRODUCT.md`'s notes on the look are brought into line.

## Capabilities

### New Capabilities
- `design-tokens`: the one token file every page's colours, fonts, sizes and radii come from, and the rule that templates and stylesheets use its named roles only.
- `site-layout`: what every page shares: the header (name, search and location bar, the four links), breadcrumbs, the footer with the tagline and credits, the filter rail and map panel layout, and how they fold on phones.

### Modified Capabilities
- `site-identity`: the tagline moves from the masthead to the footer.
- `act-index`: the search box moves into the header bar, beside the name; the header's link to the index reads "Bands"; the index drops the 40-entry pages and the inverted "The" for one guide line per letter and names printed as they are.
- `saved-shows`: the header link reads "Saved" with the count in a yellow badge, in place of "Saved shows (3)".

The venue list, venue pages, the venue booking view, event pages, the event listing and band discovery are described by specs that are still inside their own unarchived changes (`add-venue-list`, `add-venue-pages`, `add-event-pages`, `add-band-discovery-swipe`, `improve-band-discovery`), so this change can't carry deltas for them yet. Their behaviour is unchanged here; where one of them fixes a look (the venue page's plum tab, for example), its wording is brought into line when that change is archived, before this one is (task group 1).

## Impact

- **Templates:** all of `core/templates/core/`, `core/templates/calendar/calendar.html` and `core/templates/map/map.html`. `core/templates/admin/` is untouched.
- **Styles:** `core/static/core/scss/` (17 files) removed; `core/static/core/css/tokens.css` and `core/static/core/css/site.css` added; the built file is not committed.
- **Scripts:** `saved_shows.js` (the count badge), `search-suggest.js` (the box's new place), `discover.js`, `town_chips.js`, `location.js` and the inline burger script in `base.html`, where they find elements by class names that change.
- **Stored HTML:** each event's listing row is stored (`Event.baked_html_template`), so `resave_all_events` is run once at deploy.
- **Dependencies:** adds `django-tailwind-cli` (which fetches Tailwind's standalone program at build time); removes `django-sass-processor` and `libsass`. Adds self-hosted Inter Tight and Geist Mono font files (both SIL Open Font License); no font is loaded from another site.
- **Build and deploy:** `bin/build.sh` and the `Dockerfile` run the Tailwind build in place of `compilescss`; the test runner builds the stylesheet once before browser tests.
- **Tests:** tests that look for old class names or the masthead's wording change with the templates; new tests cover the token rule, the header, breadcrumbs and the folded layouts.
- **No model, migration, URL or data change.** No new external service.
