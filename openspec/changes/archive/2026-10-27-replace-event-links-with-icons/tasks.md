## 1. The icon row

- [x] 1.1 Add `core/event_actions.py`: `PLACEHOLDER`, `actions_html(event, saved_ids, next_url)`, built with `format_html` (calendar file, Google Calendar, map when located, share, then the save form button with its state), and `with_actions`. Verify with 1.5.
- [x] 1.2 Add the `event_html` template tag (`core/templatetags/event_actions.py`), which parses the visitor's saved shows once per request and fills the placeholder. Use it in `index.html`, `saved.html` and `search.html`, which moves off the live `event.html` include. Verify with 1.5.
- [x] 1.3 In `event.html`, replace the inline links and their "+" separators with the placeholder, after the tix column and before the play buttons, and tidy the "//" separators. Add `core/templates/core/icons.html`, with the SVG symbols, included once in `base.html`. Style the row in `core.scss`: its own row, indented with the text, with icon colours and the saved fill. Verify with 1.5.
- [x] 1.4 Update the `/saved` page's wording from "SAVE link" to the bookmark. Verify by reading the page.
- [x] 1.5 Add `core/tests/test_event_actions.py`, covering:
  - icons with names, in order;
  - no map without a location, or with a venue override;
  - the row in its own place, before the play buttons;
  - search results;
  - not in the stored HTML;
  - icons defined once;
  - the saved state shown on load, from the server.

  Update the existing render tests that looked at links in the stored HTML. Verify that they pass.

## 2. Saving without JavaScript

- [x] 2.1 Add the `/saved/toggle/<id>` view (POST only): it parses the cookie, toggles the ID (newest first, at most 300, existing events only), sets the cookie as the script writes it, and redirects to `next` when it's on this site, or else to `/`. Verify with 2.3.
- [x] 2.2 Update `saved_shows.js` to work on the bookmark button: stop the form submitting, toggle in place, update the title, `aria-label`, `aria-pressed` and fill on every copy, and no longer reveal a hidden link. Verify with 2.4.
- [x] 2.3 Add toggle tests: adding and removing, the limit, an unknown event, an off-site `next`, and GET refused. Verify that they pass.
- [x] 2.4 Update `core/tests/test_saved_shows_browser.py` for the bookmark: save, unsave, state on load, the map copy, and the count. Add saving with JavaScript off, through the form, landing back at the event filled. Verify that it passes offline.

## 3. Roll out

- [x] 3.1 Measure the homepage's render time with all upcoming events, before and after, and record both in this task. Verify that the difference is acceptable, or add caching for the row.
  - 2026-10-27, local homepage, 949 events, median of 7: stored HTML alone 58 ms and 1.4 MB; with the rows built by `reverse` and `format_html`, 190 ms; with plain strings, 83 ms (+25 ms) and 2.4 MB. Render serves pages with Brotli (the live 1.4 MB page arrives as 345 KB), and the rows' repeated markup compresses well. Acceptable, with no caching.
- [x] 3.2 Run the whole suite with outbound network blocked, then `resave_all_events` locally, and check the row, the hover names and saving with and without JavaScript in a browser. Note the one-off Render re-render in `PRODUCTION.md`. Verify that the tests pass and the page works by hand.
