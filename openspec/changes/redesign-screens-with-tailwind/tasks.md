# Tasks

Each screen is built from its Paper artboard's code export (exact values, never screenshots), translated to the token roles. Each group's commit includes its tests; the suite passes at the end of every group except where a group says a later one finishes the move.

## 1. Before starting

- [ ] 1.1 Confirm with the owner that every page takes the home page's header, including the five screens drawn with the other one (design.md, decision 5 and Open Questions). Done when the answer is recorded in design.md.
- [ ] 1.2 Archive the finished changes whose specs this redesign touches (`add-venue-pages`, `add-venue-list`, `add-event-pages`), or record why one can't be yet. Done when `openspec list` no longer shows the archived ones and their specs are in `openspec/specs/`.
- [ ] 1.3 For each spec that 1.2 brought in, add a delta here for any requirement that fixes the old look (tabs, strips, the venue page's fact line, the event page's date tab, the listing's "SHOW MAP" wording). Done when `openspec validate redesign-screens-with-tailwind` passes with them.

## 2. Tailwind and the token file

- [ ] 2.1 Add `django-tailwind-cli` to `requirements.txt` (installed with `uv pip install`), with the Tailwind version pinned in settings; confirm the setting names against the package's documentation. Done when `venv/bin/python manage.py tailwind build` writes the stylesheet.
- [ ] 2.2 Write `core/static/core/css/tokens.css`: Paper's scales (from the file's token export, Tailwind format) and the roles in design.md's table, including the named type sizes. Done when a test reads the file and finds every role in the `design-tokens` spec, with the shipped values for the accent, link, and the three fonts.
- [ ] 2.3 Add Inter Tight and Geist Mono as font files under `core/static/core/fonts/` with their licence files, and `@font-face` rules in `core/static/core/css/site.css`. Done when a test finds no `http` URL in `site.css` or `tokens.css`.
- [ ] 2.4 Write `site.css`: the Tailwind and token imports, `.prose-site` for editors' rich text, and the overrides for accessible-autocomplete's menu and MapLibre's controls. Done when the build succeeds and a test page with rich text shows styled headings, lists and links in a browser test.
- [ ] 2.5 Add the token rule test: scan `core/templates/` (not `admin/` or `core/email/`) and `core/static/core/css/` other than `tokens.css` for literal colours, arbitrary-colour classes, colour-scale classes and literal fonts. Done when it fails on a planted `#8b5b8b`, `bg-[#8b5b8b]` and `text-gray-700`, naming the file and value, and those plants are removed. (It passes over the whole tree only at the end of group 9.)
- [ ] 2.6 Test that changing a role restyles the site: build with the accent set to `#FF6B00` and the display font to Georgia into a temporary file, and check in a browser test that a ticket price, a "Tonight" tag and a page heading follow. Done when that test passes.
- [ ] 2.7 Build the stylesheet in the test runner when the Tailwind program is present and the built file is older than its sources; skip browser tests with a message naming the command when it's absent. Done when `manage.py test` on a fresh checkout without the program runs every non-browser test and reports the skip.
- [ ] 2.8 Replace `compilescss` with the Tailwind build in `bin/build.sh` and the `Dockerfile`, and update `AGENTS.md` ("Running it") and `PRODUCTION.md`. Done when `bin/build.sh` run locally produces the stylesheet and `collectstatic` collects it.

## 3. The page shell

- [ ] 3.1 Rebuild `core/templates/core/base.html` on the new stylesheet, from the home artboard's top bar: the name, the search box, "Bands & artists", "Venues", "Submit a show", "Saved"; the messages block, the content block and the footer (footer links, Privacy, Terms, the OpenStreetMap credit, the name and tagline). Remove the burger menu and its script. Done when tests for the `site-layout` header and footer scenarios and the `site-identity` tagline scenarios pass.
- [ ] 3.2 Move the search box into the header and restyle its suggestions from "Search — suggestions as you type" (group labels, the kind in small caps, the marked part, place or date, the chosen row on the accent, "See all results"), keeping `search-suggest.js`'s behaviour and what screen readers hear. Done when the `act-index` search-box and suggestion scenarios and the existing suggestion browser tests pass.
- [ ] 3.3 Change the header's saved link to "Saved" with the count badge in `saved_shows.js`, named "Saved, 3 shows" for screen readers. Done when the `saved-shows` header scenarios pass in the existing browser test, updated.
- [ ] 3.4 Add the breadcrumbs part and a small helper each view uses to say its path. Done when tests for the show, band and home breadcrumb scenarios pass.
- [ ] 3.5 Fold the header below 640px (the links behind "Menu", the search box on its own row). Done when a browser test at 390px finds no sideways scroll on the home page and reaches each link through "Menu".
- [ ] 3.6 Keyboard and contrast: a visible focus mark on every header control, and a test computing the contrast of each text role on its ground from the token file. Done when the `site-layout` keyboard and contrast scenarios pass.

## 4. Shared parts

- [ ] 4.1 Build the parts as includes: rail, page head, week strip, day map, show row, date block, fact table, tag, pill, button. Done when each renders in a template test with the classes its artboard gives, using roles only.
- [ ] 4.2 Rail: groups under small caps labels, the location field with "Change" opening the existing location form in place ("Set your location" without one), folding behind "Filters" below 1024px. Done when tests for the rail scenarios pass, including a browser test that changes the location from the home page and lands back there, and one that opens the filters at 390px and applies one.
- [ ] 4.3 Day map, from "Home — map shown": the existing MapLibre day map opened by "Show on map" beside the day's count, above the day's rows; the "N of M shows on the map" line; the callout with the show's name, venue, time and link; "Hide map"; token colours for pins, callout and location dot; nothing loaded until opened; no link without a tiles key or a pinnable show. Done when browser tests for the `site-layout` map scenarios pass with tile requests stubbed.

## 5. Home and the event listing

- [ ] 5.1 Rebuild `core/templates/core/index.html` from "Home (alternative)": the rail (location, region, state, metro, town and neighborhood filters, month calendar, calendar subscription), the first day's page head ("Tonight" or the day's name, the count line's three wordings), and each later day under its own date heading. Done when tests for the `site-layout` "opens with today" scenarios, the existing geo filter tests and the listing tests pass.
- [ ] 5.2 Week strip: seven days from the first listed day with counts from the events already grouped by day, the first marked, each a link to its day's heading, "No shows" unlinked. Done when tests for the week strip scenarios pass, including counts under a state filter.
- [ ] 5.3 Rebuild `core/templates/core/event.html` as the new row (time, name and openers, venue line with place, distance and ages, price on the accent or "FREE", the bookmark at the end), with the four link icons and the play buttons on a second line, keeping the save toggle, play button and anchor hooks; stacking below 640px. Done when the `site-layout` row scenarios, the `event-action-icons` delta's scenarios and the existing listing, saved-shows and artist-preview tests pass against the new row.
- [ ] 5.4 Month archive pages and `calendar/calendar.html`: the same row, and the month grid in the rail's calendar style. Done when the archive page tests pass and a browser test at 390px finds no sideways scroll.
- [ ] 5.5 Test that `resave_all_events` re-renders a stored row into the new markup. Done when that test passes.

## 6. Event page, search and Saved shows

- [ ] 6.1 Rebuild `core/templates/core/event_page.html` from "Event — page": breadcrumbs through the venue; the date and time line; the headliner with "Tonight" when it is; openers as links; the bar of "Tickets", "Save", "Venue's page" and the calendar, Google Calendar and share links; "Listen first"; "About this show"; the fact table (venue, distance and directions, price, ages, access, each only when known); "Next at <venue>" with its next three approved shows; cancelled and past notices. Done when the existing event page tests pass and new tests cover "Next at <venue>" and the breadcrumbs.
- [ ] 6.2 Rebuild `core/templates/core/search.html` and `search_show.html` from "Search — results": the searched words as the heading with the count, the "Jump to" rail with each section's count, a section per kind, the marked part in each name, upcoming shows as rows with their date, past shows as plain rows, the nothing-found message. Done when the existing search tests pass and a test checks the rail's counts match the sections.
- [ ] 6.3 Rebuild `core/templates/core/saved.html` from "Saved shows": the rail (location, how saving works, the Discover link), the heading with the count of shows and nights, "Show on map" opening the existing all-shows map, days as headings over rows, the empty message. Done when the `saved-shows` delta's scenarios, the existing saved-shows tests and the map browser test pass.

## 7. Venues and bands

- [ ] 7.1 Rebuild `core/templates/core/venue_list.html` from "Venues — listing" under the shared header: heading with the count line, the rail (place, genre, "Takes open bookings"), rows with the upcoming-show link and the "Open booking" tag, and no always-open map panel. Done when the existing venue list tests and browser test pass, updated for markup only.
- [ ] 7.2 Rebuild `core/templates/core/venue.html` and `venue_tabs.html` from "Venue — page": name, fact line, genre pills, "Website" and "Directions", the "Shows" and "For artists" tabs, "The bill" with date blocks and the "Tonight" tag, the fact table (rows only when known), "Want to play here?" when the venue takes bookings. No map. Done when the existing venue page tests pass and a test confirms no map element is drawn.
- [ ] 7.3 Restyle `core/templates/core/venue_booking.html` with the same header, tabs and fact table. Done when the booking view's tests pass.
- [ ] 7.4 Rebuild `core/templates/core/act_index.html` and `index_entry.html` from "Bands — listing": the letter rail across the page, each letter's initial with its count and guide line, two columns of entries with kind, town and the next show's date (on the accent when it's within a week), and the "Not sure who to see?" box linking to Discover. Done when the `act-index` delta's scenarios and the existing index tests pass, including the 390px one.
- [ ] 7.5 Rebuild `core/templates/core/band.html` from "Band — page": the act's photo when it has one, kind and origin label, name, genre pills, play buttons, the "Next show" band with Save and Tickets, upcoming shows with date blocks, members, links, "Is this you?", About with its Wikipedia credit, and the genre credit. Done when the existing band page, Bandcamp and preview tests pass.
- [ ] 7.6 Rebuild `core/templates/core/discover.html` and adjust `discover.js` selectors from "Discover bands": intro and filters at the left, the card with player, name, next show and buttons, "Skip" and "Add shows", "Your picks" at the right. Done when the existing discover tests and browser tests pass.

## 8. The pages with no artboard

- [ ] 8.1 Forms: submit a show, the location form's page, the calendar subscription and the digest pages, with one set of field, label, error and button styles. Done when their tests, including the digest form browser test, pass.
- [ ] 8.2 Static pages, privacy and terms in `.prose-site`, and the iOS install prompt. Done when the static, privacy and public page tests pass.
- [ ] 8.3 The digest email takes the new colours in its inline styles only. Done when the digest mail tests pass and its HTML contains none of the old plum or lavender values.

## 9. Removing the old styles

- [ ] 9.1 Delete `core/static/core/scss/`, the `sass_tags` loads, `sass_processor` from settings, and `django-sass-processor` and `libsass` from `requirements.txt`. Done when `grep -r "sass" core nycnoise requirements.txt` finds nothing and the suite passes.
- [ ] 9.2 Add the every-page test: request each public URL pattern and check the response loads the new stylesheet and has the header. Done when it passes.
- [ ] 9.3 Run the token rule test (2.5) over the whole tree. Done when it finds nothing.
- [ ] 9.4 Rewrite `DESIGN.md` for the new system (tokens, type, layout, parts, do's and don'ts) and bring `PRODUCT.md` into line. Done when neither names plum, lavender or the 42em column as current.
- [ ] 9.5 Run the whole suite with outbound network blocked. Done when it passes.
- [ ] 9.6 Capture each built screen at 1440px beside its artboard, and the home, event, venue and band pages at 390px, from the running site, for the owner's acceptance (G4). Done when the screenshots are in the change's folder and any difference from an artboard is listed with its reason.

## Workflow follow-up

- At deploy, run `resave_all_events` once, so stored listing rows take the new markup (design.md, Migration Plan).
- Propose the left-out filters (design.md, Follow-ups) as their own changes.
- Archive this change only when every scenario has a passing test and every task is checked.
