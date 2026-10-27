## Context

- **Visitors have no accounts.** The site has no login apart from the admin.
- **Event HTML is stored, and shared.** Each event's HTML is stored in `Event.baked_html_template` (`core/utils_event_caching.bake_event_html`) and served to every visitor alike. So nothing visitor-specific can be baked in: whether a show is saved has to be applied in the browser after the page loads.
- **Events are listed on several pages.** The homepage and month archive group events by date in `core/views/index.py`, and render each with `event.get_baked_html`. The day maps' panel shows copies of event elements (`map.html`), and a click handler on `document` (`artist_preview.js`) already covers those copies.
- **The header** comes from `MenuItem` rows in the database (`core/templatetags/menu_items.py`), rendered in `base.html`.
- **A remembered setting already exists:** the region, state and metro filter is kept in a cookie (`geo_filter`) by `core/geo_filters.py`, read and written on the server.

## Goals / Non-Goals

**Goals:**
- One click to save, with no sign-up, and nothing about the visitor stored on the server.
- A Saved shows page rendered on the server from the same stored event HTML, so saved events look and behave exactly as they do in the listing.

**Non-Goals:**
- Accounts, or syncing saved shows across browsers and devices.
- Grouping by venue, artist or location (later), reminders, sharing a list of saved shows, and calendar export of all saved shows.

## Decisions

**1. A cookie holding event IDs, not `localStorage`.**
- **What it holds:** `saved_shows`, a comma-separated list of event IDs, newest first, for a year, `SameSite=Lax`.
- **Why a cookie:** the server can read it, so `/saved` is rendered on the server like the homepage, with the same date grouping and the same stored HTML, and needs no API. With `localStorage`, the page would have to send IDs to a JSON endpoint and build the listing in JavaScript.
- **Size:** 300 IDs of up to 5 digits is about 1.8 KB, well under the 4 KB cookie limit.
- **Who writes it:** JavaScript writes it on each save, and the server rewrites it on `/saved` to drop IDs that can't be shown. It isn't `HttpOnly`, because the script must read it. That's fine: it holds only public event IDs.
- **Alternative rejected:** server-side storage keyed by the session. It would need sessions for anonymous visitors, and storage and cleanup, with no gain until there are accounts.

**2. SAVE is a link in the event's line of links, set in the browser.**
- **The markup:** `event.html` renders `+ <a href="/saved" class="save" data-event-id="{{ event.pk }}" hidden>SAVE</a>` after SHARE. It's the same for every visitor, and `hidden` keeps it out of view without JavaScript.
- **On load,** `saved_shows.js` reads the cookie, un-hides every `a.save`, and sets the text to SAVED or SAVE, with `aria-pressed`.
- **On click,** a handler on `document` toggles the ID in the cookie, then updates every `a.save` with that ID, which covers the map panel's copies, and the header count.
- **Why a link, not a button:** it matches ICAL, GCAL, MAP and SHARE, which are all links. Its `href` points at `/saved`, in case a click lands before the script runs.

**3. The `/saved` view reuses the index grouping.**
- **How it works:** the view reads and cleans the cookie's IDs: positive whole numbers, without repeats, at most 300. It then fetches `Event.objects` (approved only) with `starttime` from the start of today in New York time, ordered like the index, with `select_related("venue")`, and groups them by date with the same helper the index uses.
- **The refactor:** the grouping in `core/views/index.py` is moved into a shared function, so both views use it. No geo filter is passed, and the geo cookie isn't touched.
- **The cookie:** the response rewrites it to the IDs found, keeping their order.
- **`group`:** it's parsed into a value with only `date` allowed, so later groupings slot in as new values and templates.

**4. The header link.**
- **The markup:** `base.html` adds a fixed "Saved shows" link next to the menu items, `<a href="/saved" class="saved-count">`.
- **Why not a `MenuItem` row:** that would make the feature depend on an admin entry existing.
- **The count:** the script sets it from the cookie on load and on each change. Without JavaScript, the link shows no count.

**5. Rolling it out.** Adding the SAVE link changes `event.html`, so the stored events are re-rendered once with `resave_all_events`, locally and on Render, after deploying.

**How it's tested.** No outside service is involved, so nothing needs mocking.
- **Server-side Django tests** set the cookie on the test client. They cover:
  - grouping and order, and the area filter being ignored;
  - past, deleted and unapproved events dropped, and the rewritten cookie;
  - malformed values, and the 300 cap;
  - the empty state, and unknown `group` values;
  - the SAVE link's markup, including that it's hidden without JavaScript.
- **Browser tests** use Playwright with the live test server, aborting every outside request, as the play-button tests do. They cover:
  - save and unsave, and the cookie's contents;
  - state on load, and the map panel's copies updating;
  - the header count updating;
  - the link staying hidden with JavaScript off.

## Risks / Trade-offs

- **[Saved shows are per browser]** → The page says so ("saved in this browser"). If people want them on every device, accounts are a separate proposal.
- **[Clearing cookies loses saved shows]** → Accepted for now. A later "copy a link to my saved shows" (IDs in the URL) could serve as a backup, and as a way to share.
- **[Re-rendering every stored event to add the link]** → It's a one-off `resave_all_events`, which takes seconds locally (2,942 events in about 12 seconds). Until it runs, events simply have no SAVE link.
- **[The count includes shows the page will drop]** → Visiting `/saved` tidies the cookie, so the count corrects itself.

## Migration Plan

1. Deploy.
2. Run `resave_all_events` on Render, so stored events get the SAVE link.

**Rollback:** revert, and re-render again. Visitors' cookies are harmless if left behind.
