Issue: [#36 Use the same header and nav menu on every page](https://github.com/natea/newenglandmusic/issues/36)

# Tasks

## 1. The one menu
- [ ] 1.0 Check the real menu items (read-only, in the admin) and list those with "show in header" off that are in the footer; the owner decides whether to flag any or add a migration. Name the chosen sketch in the design.
- [ ] 1.1 Replace the header links and the hidden ☰ list in the base template with one menu list rendered once, with a real button, as `nav#siteMenu`, keeping the Saved shows link's `.saved-count` element; remove the inline toggle script and the hidden list, delete the unused `get_all_menu_items` tag, and remove the old `#burgerMenuContents` and `burgerColumn` styles. Check the header-to-content spacing (the removed 50px bottom margin, pages with the month header), scope or replace the `.rightColumn :first-child` rule, and put Saved shows last.
- [ ] 1.2 Style it: a row of links above 600px, a ☰ button and a stacked column below; drop the `|` separators; keep links from squeezing.
- [ ] 1.3 Add the small deferred static toggle script (aria-expanded, keyboard) that adds the `js` class from a tiny inline head snippet before first paint (no flash on phones); without it the list stays shown and the button hidden.
- [ ] 1.4 Tests for the scenarios in `site-navigation`: identical menu markup across the listed pages, one list only, edits in the admin showing everywhere, links across the top on wide screens, ☰ on narrow ones opening and closing by tap and keyboard (Playwright at two sizes), no-JavaScript reachability, the Saved shows count still updating, and the fixture's header-flagged items (listing, venues, artists, about, Discover) linked.
- [ ] 1.5 Update `test_discover.py` and `test_search_kinds.py`, which read the old `burgerMenuContents` block, to use `nav#siteMenu`: the search test must still check that the search input is not inside the nav, and the Discover test must compare the nav, the search form and the footer.

## 2. The listing's folding controls
- [ ] 2.1 In `index.html` only, wrap the geo filter and location form in one closed `<details>` with a summary of what applies and the "show all" link beside it; keep the subscribe box collapsed, pass the saved location from the view for the summary, omit the section when neither control renders, and leave Discover and saved shows unchanged.
- [ ] 2.2 Style the section, and check the filter's auto-submit script and cookie behaviour still work inside it, and update `test_location_browser.py` (open the section first) and check `test_index_geo_filter.py`, `test_metro_towns.py`, `test_discover_filter.py` and the saved-shows tests.
- [ ] 2.3 Tests for the `event-geo-filter` scenarios: collapsed by default, the summary naming state and location, the "show all" link reachable while closed, Discover and saved shows unchanged, the section still closed with a filter active, only one or neither control rendering, the month archive, filtering still working and setting the cookie, and working without JavaScript.

## 3. Wrap up
- [ ] 3.1 Resolve the design's open questions with the owner (which items, picker, advanced search, sketch), and add a menu-item migration only if they ask.
- [ ] 3.2 Run the full test suite with the network blocked.
