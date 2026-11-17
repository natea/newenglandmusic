# Tasks

Each screen is built from its Paper artboard's code export (exact values, never screenshots), translated to the token roles. Each group's commit includes its tests; the suite passes at the end of every group except where a group says a later one finishes the move.

## 1. Before starting

- [ ] 1.1 Confirm with the owner which home page is built (design.md, Open Questions). Done when the answer is recorded in design.md and, if it's the alternative home, groups 4 and 5 and the `site-layout` spec are revised first.
- [ ] 1.2 Archive the finished changes whose specs this redesign touches (`add-venue-pages`, `add-venue-list`, `add-event-pages`), or record why one can't be yet. Done when `openspec list` no longer shows the archived ones and their specs are in `openspec/specs/`.
- [ ] 1.3 For each spec that 1.2 brought in, add a delta here for any requirement that fixes the old look (tabs, strips, the venue page's fact line). Done when `openspec validate redesign-screens-with-tailwind` passes with them.

## 2. Tailwind and the token file

- [ ] 2.1 Add `django-tailwind-cli` to `requirements.txt` (installed with `uv pip install`), with the Tailwind version pinned in settings; confirm the setting names against the package's documentation. Done when `venv/bin/python manage.py tailwind build` writes the stylesheet.
- [ ] 2.2 Write `core/static/core/css/tokens.css`: Paper's scales (from the file's token export, Tailwind format) and the roles in design.md's table, including the named type sizes. Done when a test reads the file and finds every role in the `design-tokens` spec, with the shipped values for the accent, link, and the three fonts.
- [ ] 2.3 Add Inter Tight and Geist Mono as font files under `core/static/core/fonts/` with their licence files, and `@font-face` rules in `core/static/core/css/site.css`. Done when a test finds no `http` URL in `site.css` or `tokens.css`.
- [ ] 2.4 Write `site.css`: the Tailwind and token imports, `.prose-site` for editors' rich text, and the overrides for accessible-autocomplete's menu and MapLibre's controls. Done when the build succeeds and a test page with rich text shows styled headings, lists and links in a browser test.
- [ ] 2.5 Add the token rule test: scan `core/templates/` (not `admin/` or `core/email/`) and `core/static/core/css/` other than `tokens.css` for literal colours, arbitrary-colour classes, colour-scale classes and literal fonts. Done when it fails on a planted `#8b5b8b`, `bg-[#8b5b8b]` and `text-gray-700`, naming the file and value, and those plants are removed. (It passes over the whole tree only at the end of group 9.)
- [ ] 2.6 Test that changing a role restyles the site: build with the accent set to `#FF6B00` and the display font to Georgia into a temporary file, and check in a browser test that the search button, a "Tonight" tag and a page heading follow. Done when that test passes.
- [ ] 2.7 Build the stylesheet in the test runner when the Tailwind program is present and the built file is older than its sources; skip browser tests with a message naming the command when it's absent. Done when `manage.py test` on a fresh checkout without the program runs every non-browser test and reports the skip.
- [ ] 2.8 Replace `compilescss` with the Tailwind build in `bin/build.sh` and the `Dockerfile`, and update `AGENTS.md` ("Running it") and `PRODUCTION.md`. Done when `bin/build.sh` run locally produces the stylesheet and `collectstatic` collects it.

## 3. The page shell

- [ ] 3.1 Rebuild `core/templates/core/base.html` on the new stylesheet: the header part (name, search and location bar with the yellow button, the four links with icons), the messages block, the content block and the footer (footer links, Privacy, Terms, the OpenStreetMap credit, the name and tagline). Remove the burger menu and its script. Done when tests for the `site-layout` header and footer scenarios and the `site-identity` tagline scenarios pass.
- [ ] 3.2 Move the search box into the bar, keeping `search-suggest.js` working and one box on the results page. Done when the `act-index` search-box scenarios and the existing suggestion browser tests pass.
- [ ] 3.3 Show the saved location in the bar ("Set your location" without one), opening the existing location form in a popover, with a plain link to the form's page without JavaScript. Done when tests for the three location scenarios pass, including a browser test that sets a location from `/venues` and lands back there.
- [ ] 3.4 Change the header's saved link to "Saved" with the count badge in `saved_shows.js`, named "Saved, 3 shows" for screen readers. Done when the `saved-shows` header scenarios pass in the existing browser test, updated.
- [ ] 3.5 Add the breadcrumbs part and a small helper each view uses to say its path. Done when tests for the venue, band and home breadcrumb scenarios pass.
- [ ] 3.6 Fold the header below 640px (icons with screen-reader names, the bar on its own row). Done when a browser test at 390px finds no sideways scroll on the home page and each link's accessible name.
- [ ] 3.7 Keyboard and contrast: a visible focus mark on every header control, and a test computing the contrast of each text role on its ground from the token file. Done when the `site-layout` keyboard and contrast scenarios pass.

## 4. Shared parts

- [ ] 4.1 Build the parts as includes: filter rail, map panel, show row, date block, poster tile, tag, pill, button. Done when each renders in a template test with the classes its artboard gives, using roles only.
- [ ] 4.2 Poster tile: the ground chosen from the event's ID, the name in display capitals over the mono line. Done when a test shows the same event always gets the same ground and five consecutive IDs don't all share one.
- [ ] 4.3 Map panel: the existing MapLibre map in a sticky 440px panel, open from 1024px, behind "Map" below; pins, callout and location dot in token colours; no panel without a tiles key. Done when browser tests for the `site-layout` map scenarios pass with tile requests stubbed.
- [ ] 4.4 Filter rail: groups under labels, folding behind "Filters" below 1024px. Done when a browser test opens the filters at 390px and applies one.

## 5. Home and the event listing

- [ ] 5.1 Rebuild `core/templates/core/index.html` from the "Home (Eventbrite-style)" artboard: the heading (three wordings), the rail holding the region, state, metro, town and neighborhood filters and the calendar subscription, day sections, and the map panel. Done when tests for the heading scenarios, the existing geo filter tests and the listing tests pass.
- [ ] 5.2 Rebuild `core/templates/core/event.html` as the new row (tile, title, openers, time, venue line with distance and ages, price, save), keeping the save toggle, action icons, play buttons and anchor hooks. Done when the existing listing, action-icon, saved-shows and artist-preview tests pass against the new row.
- [ ] 5.3 Month archive pages and `calendar/calendar.html`: the compact row (no tile) and the month grid in the new tokens. Done when the archive page tests pass and a browser test at 390px finds no sideways scroll.
- [ ] 5.4 Test that `resave_all_events` re-renders a stored row into the new markup. Done when that test passes.

## 6. Venues

- [ ] 6.1 Rebuild `core/templates/core/venue_list.html` from "Venues — listing": heading with the count line, the rail (place, genre, "Takes open bookings"), rows with the upcoming-show link and the "Open booking" tag, the map panel. Done when the existing venue list tests and browser test pass, updated for markup only.
- [ ] 6.2 Rebuild `core/templates/core/venue.html` and `venue_tabs.html` from "Venue — page": name, fact line, genre pills, "Website" and "Directions", the "Shows" and "For artists" tabs, "The bill" with date blocks and the "Tonight" tag, the fact table (rows only when known), "Want to play here?" when the venue takes bookings. No map. Done when the existing venue page tests pass and a test confirms no map element is drawn.
- [ ] 6.3 Restyle `core/templates/core/venue_booking.html` with the same header, tabs and fact table. Done when the booking view's tests pass.

## 7. Bands

- [ ] 7.1 Rebuild `core/templates/core/act_index.html` and `index_entry.html` from "Bands — listing": the letter rail across the page, each letter's initial with its count and guide line, two columns of entries with kind, town and the next show's date (a yellow tag when it's within a week), and the "Not sure who to see?" box linking to Discover. Done when the `act-index` delta's scenarios and the existing index tests pass, including the 390px one.
- [ ] 7.2 Rebuild `core/templates/core/band.html` from "Band — page": tile or photo, kind and origin label, name, genre pills, play buttons, the "Next show" band with Save and Tickets, upcoming shows with date blocks, members, links, "Is this you?", About with its Wikipedia credit, and the genre credit. Done when the existing band page, Bandcamp and preview tests pass.
- [ ] 7.3 Rebuild `core/templates/core/discover.html` and adjust `discover.js` selectors from "Discover bands": intro and filters at the left, the card with player, name, next show and buttons, "Skip" and "Add shows", "Your picks" at the right. Done when the existing discover tests and browser tests pass.

## 8. The pages with no artboard

- [ ] 8.1 Event page (`event_page.html`): date block, bill, tickets and venue buttons, fact table, play buttons, breadcrumbs through the venue. Done when the event page tests pass.
- [ ] 8.2 Search results (`search.html`, `search_show.html`): sections per kind with counts, compact show rows, marks kept. Done when the search tests pass.
- [ ] 8.3 Saved shows (`saved.html`) with its map in the panel. Done when the saved-shows tests and map browser test pass.
- [ ] 8.4 Forms: submit a show, the location form's page, the calendar subscription and the digest pages, with one set of field, label, error and button styles. Done when their tests, including the digest form browser test, pass.
- [ ] 8.5 Static pages, privacy and terms in `.prose-site`, and the iOS install prompt. Done when the static, privacy and public page tests pass.
- [ ] 8.6 The digest email takes the new colours in its inline styles only. Done when the digest mail tests pass and its HTML contains none of the old plum or lavender values.

## 9. Removing the old styles

- [ ] 9.1 Delete `core/static/core/scss/`, the `sass_tags` loads, `sass_processor` from settings, and `django-sass-processor` and `libsass` from `requirements.txt`. Done when `grep -r "sass" core nycnoise requirements.txt` finds nothing and the suite passes.
- [ ] 9.2 Add the every-page test: request each public URL pattern and check the response loads the new stylesheet and has the header. Done when it passes.
- [ ] 9.3 Run the token rule test (2.5) over the whole tree. Done when it finds nothing.
- [ ] 9.4 Rewrite `DESIGN.md` for the new system (tokens, type, layout, parts, do's and don'ts) and bring `PRODUCT.md` into line. Done when neither names plum, lavender or the 42em column as current.
- [ ] 9.5 Run the whole suite with outbound network blocked. Done when it passes.
- [ ] 9.6 Capture each of the seven screens at 1440px, and the home, venue and band pages at 390px, from the running site, beside their artboards, for the owner's acceptance (G4). Done when the screenshots are in the change's folder and any difference from an artboard is listed with its reason.

## Workflow follow-up

- At deploy, run `resave_all_events` once, so stored listing rows take the new markup (design.md, Migration Plan).
- Propose the left-out filters (design.md, Follow-ups) as their own changes.
- Archive this change only when every scenario has a passing test and every task is checked.
