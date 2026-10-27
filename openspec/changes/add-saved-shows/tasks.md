## 1. Saved shows page

- [x] 1.1 Move the date grouping out of `core/views/index.py` into a shared function, taking a queryset and returning the date groups. Verify that the existing index, archive and geo-filter tests still pass.
- [x] 1.2 Add `core/saved_shows.py`:
  - `parse_saved(cookie)`: positive whole numbers, without repeats, in order, at most 300;
  - `format_saved(ids)`;
  - `COOKIE_NAME = "saved_shows"`, and a one-year `max_age`.

  Verify with 1.4.
- [x] 1.3 Add the `/saved` view and URL, and a template `core/saved.html`. The view lists approved events from the start of today in New York time, ordered like the index, grouped by date with the shared function, rendered with each event's stored HTML. It:
  - ignores the geo filter, and doesn't touch its cookie;
  - rewrites `saved_shows` to the IDs found;
  - parses `group`, allowing only `date`;
  - says "saved in this browser" in a note;
  - has an empty state explaining SAVE.

  Verify with 1.4.
- [x] 1.4 Add `core/tests/test_saved_shows.py`. Verify that it passes. It covers every page scenario in the spec:
  - grouped by date;
  - the area filter ignored, and the geo cookie unchanged;
  - nothing saved;
  - an unknown group;
  - past, deleted and unapproved shows dropped, with the rewritten cookie;
  - a malformed cookie;
  - the 300 limit, for parsing.

## 2. SAVE link and header

- [x] 2.1 In `event.html`, add `+ <a href="/saved" class="save" data-event-id="…" hidden>SAVE</a>` after SHARE. In `base.html`, add a header "Saved shows" link (`a.saved-count`) and load `core/js/saved_shows.js`. Verify with 2.3 and 2.4.
- [x] 2.2 Write `core/static/core/js/saved_shows.js`. Verify with 2.4. It:
  - reads and writes the cookie: newest first, at most 300, the oldest dropped, renewed for a year, `SameSite=Lax`, path `/`;
  - un-hides and labels every `a.save` on load, with `aria-pressed`;
  - toggles on click, through a handler on `document`, updating every copy with the same ID and the header count.
- [x] 2.3 Add render tests to `core/tests/test_saved_shows.py`. Verify that they pass. They check that:
  - the SAVE link is in each event's stored HTML, after SHARE, `hidden`, with its event ID;
  - the header link is on the homepage and `/saved`.
- [x] 2.4 Add `core/tests/test_saved_shows_browser.py`, a `StaticLiveServerTestCase` with Playwright that aborts outside requests. Verify that it passes offline. It covers:
  - saving a show, and unsaving it, with the cookie's contents;
  - saved state shown on load;
  - every copy of the event updating, by cloning an event into the page as the map panel does;
  - no SAVE link without JavaScript;
  - the count shown, updating, and absent when nothing is saved;
  - saving the 301st show dropping the oldest.

## 3. Roll out

- [x] 3.1 Note the one-off `resave_all_events` after deploying in `PRODUCTION.md`, and add `/saved` to the site's page list in `AGENTS.md` if one exists. Verify by reading.
- [x] 3.2 Run the whole suite with outbound network blocked, then `resave_all_events` locally, and check saving, unsaving and `/saved` in a browser. Verify that the tests pass and the page works by hand.
