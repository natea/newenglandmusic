Issue: [#36 Use the same header and nav menu on every page](https://github.com/natea/newenglandmusic/issues/36)

# Proposal

## Why

Visitors should find the same links in the same place on every page. Today every page already extends one base template, so the masthead is shared, but the navigation is not simple to use:

- The masthead shows the header links across the top (`Saved shows` plus the menu items marked "show in header") **and** a ☰ button that opens a second, hidden list of every menu item. The two lists can differ, and having both is confusing.
- On a phone the header links are squeezed together on one line.
- On the listing page the state, metro and town filter, the "near" location form and the calendar-subscribe box all sit open above the calendar and take up much of the first screen.

This was split off from #26, where feedback on the Discover page sketches asked for one universal, consistent menu. The thread settled the details: links across the top on a computer, one ☰ button on a phone.

## What Changes

- **One menu, in two forms of the same list.** The links across the top on a wide screen and the ☰ button on a narrow one show the same links, in the same order, from the same admin-edited menu items. No second hidden menu sits next to the links.
- **Phones:** the links are not squeezed onto one line; below a narrow-screen width they are replaced by a ☰ button that opens the list as a stacked column, and the button says whether it is open or closed.
- **Without JavaScript** the menu still works (the links stay reachable).
- **Every page** gets it from the shared base template; the listing, month archives, venue, band, act index, saved shows, search, Discover, static pages and forms. A test checks that the menu is identical on each.
- **The listing page's controls fold away.** The state/metro/town filter and the "near" location form share one collapsed section, and the calendar-subscribe box stays collapsed as it is now. A summary line says what is applied (for example the chosen state), so a visitor sees what is filtering without opening it. The section is always closed on load; the summary line (with a "show all" link when a filter applies) is how a visitor sees what is applied. It is built on the listing only: Discover and saved shows keep their forms as they are.
- Which links exist is not decided here: the menu shows the items marked "show in header" plus Saved shows. The hidden list of all items is dropped, so an item that is only in that list (footer-only items) loses its route from the header. Before building, the real menu items are checked and the owner decides whether any are flagged for the header or added by migration (open questions in the design).

## Capabilities

### New Capabilities

- `site-navigation`: the single site menu, shown the same on every page, as links on wide screens and a ☰ button on narrow ones.

### Modified Capabilities

- `event-geo-filter`: the listing page's filter and location controls are collapsed into one folding section.

## Impact

- **Code:** the shared base template (header and menu markup, the toggle script replacing the inline one), header styles, the listing template's filter, location and subscribe includes, and small styles for the folding section. Possibly one data migration if menu items for venues, listings or about need adding or flagging for the header (open question). The unused `get_all_menu_items` tag is deleted.
- **Tests:** existing tests read the `burgerMenuContents` block (`test_discover.py`, `test_search_kinds.py`); they are updated to the new markup, as is the location browser test, which fills the form that will now sit in a closed section.
- **No model or schema change, no new cookie, no new external API or paid call.**
- **Out of scope:** redesigning the masthead, the search box, the footer menu, and the Discover page itself.
