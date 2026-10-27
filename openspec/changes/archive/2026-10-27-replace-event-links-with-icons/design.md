## Context

- **Event HTML is stored.** Each event's HTML is stored (`Event.baked_html_template`, `core/utils_event_caching.bake_event_html`) and served as-is, because building every event's links on each view was slow in nyc noise: about 200ms a page, mostly the Google Calendar link.
- **The links are stored with it.** The links (ICAL, GCAL, MAP, SHARE and, since `add-saved-shows`, SAVE) are part of that stored HTML, inline in the event's text. Each change to them meant `resave_all_events`.
- **SAVE needs JavaScript.** The stored HTML is the same for every visitor, so SAVE was hidden until `saved_shows.js` read the cookie and labelled it.
- **Where events are listed:**
  - the homepage and month archives (`index.html`) and Saved shows (`saved.html`) render each event's stored HTML;
  - the search page (`search.html`) renders `event.html` live, for each result;
  - the day maps' panel copies event elements in the browser.

## Goals / Non-Goals

**Goals:**
- A quieter, scannable row of icons, each named on hover and for screen readers.
- No re-rendering of stored events when the row changes.
- Saving that works without JavaScript, with the right state from the first paint.

**Non-Goals:**
- Moving the play buttons out of the stored HTML. They come from the matching data, and change only when it does.
- New actions such as "copy link".

## Decisions

**1. A placeholder in the stored HTML, filled at page time.**
- **The placeholder:** `event.html` writes `<!--event-actions-->` where the row goes: after the text and the tix column, before the play buttons' row.
- **Filling it:** a template tag, `{% event_html event %}`, returns the stored HTML with the placeholder replaced by the row built by `core/event_actions.actions_html(event, saved_ids, next_url)`. All the listing templates use it, so the search page switches from the live include to the stored HTML too.
- **Alternatives rejected:**
  - **Rendering the whole event live:** the cost nyc noise moved away from.
  - **Building the row in the browser:** it fails without JavaScript, and is invisible to crawlers and link previews.

**2. The row is built as plain strings in Python, not a template include.**
- **Why:** an include would go through the template engine for about 1,000 events per page. A first version with `reverse` and `format_html` cost 137 ms per homepage view; plain strings cost about 25 ms.
- **How:** the URLs' shapes are fixed (`/event/<id>/ics`, and so on) and IDs are integers, so only the event's own text is escaped: the venue's name, the maps link, the title and the return address.
- **No `aria-label`:** an icon's `title` is also its accessible name, since it has no text, so the duplicate `aria-label`s were dropped. That's about 150 bytes a row.
- **The Google Calendar link:** it stays `/event/<id>/gcal`, a redirect, so the slow work of building Google's link is still done only when someone clicks it.

**3. Icons as one SVG symbol set per page.**
- **Where:** `core/templates/core/icons.html` defines `<symbol id="icon-ical|gcal|map|share|save">`, in a hidden `<svg>` included once in `base.html`.
- **What each row holds:** a reference per icon, `<svg><use href="#icon-…"></use></svg>`, about 80 bytes. Drawing each icon inline would add about 1.5 KB per event, about 1.5 MB on a full listing.
- **The map panel:** its copies of events refer to the same symbols, because they're in the same document.
- **Colours:** set with CSS through `currentColor`. The Google Calendar icon is blue, the map pin keeps the map's old colour, and the bookmark is filled when `.is-saved`.

**4. The bookmark is a form button.**
- **The markup:** `<form method="post" action="/saved/toggle/<id>">`, with a hidden `next` (the current path plus `#event-<id>`), around `<button class="save" aria-pressed …>`.
- **Without JavaScript:**
  - the toggle view parses the cookie, adds or removes the ID with the same rules as the script (newest first, at most 300, existing events only), sets the cookie, and redirects to `next`;
  - `next` is accepted only if `url_has_allowed_host_and_scheme` says it's on this site, and otherwise the redirect is to `/`.
- **With JavaScript:** the script stops the form submitting, toggles the cookie in place, and updates every copy of the bookmark and the header count, as before.
- **State on the first paint:** the server renders each bookmark's state from the cookie, so it's right before any script runs.
- **No CSRF check on the toggle.** Its only effect is to add or remove one public event ID in the visitor's own cookie. A cross-site form could at most bookmark a show for a visitor, which isn't worth a CSRF token in every event's form, about 1,000 per page. The view takes POST only, so links and prefetching can't trigger it.

**5. Rolling out.** One last `resave_all_events`, locally and on Render, so every stored event gets the placeholder. Until then, events without it simply show no icon row. After that, row changes need no re-render.

**How it's tested.** No outside service is involved.
- **Server-side Django tests:**
  - the row's icons, order and names;
  - no map icon without a location, or with a venue override;
  - the placeholder in the stored HTML and no links;
  - the symbols defined once;
  - the search page's row;
  - the server-side saved state from the cookie;
  - the toggle view: adding, removing, the cookie's limit, an unknown ID, and an off-site `next`.
- **Browser tests** with Playwright, aborting outside requests as before:
  - save and unsave in place, with the fill and the name;
  - the map panel's copy updating;
  - saving with JavaScript off, through the form and redirect.

## Risks / Trade-offs

- **[Page-time cost on large listings]** → Rows are a string build, and the tasks measure the homepage before and after. If it's notable, the row can be cached per event, with only the bookmark's state varying.
- **[Icons alone are less obvious than words]** → Every icon has a hover name, and familiar shapes. If people miss SAVE, a later tweak can label the bookmark.
- **[Stored HTML from before the change]** → It lacks the placeholder, and shows no row until the one-off re-render, which is part of the rollout.

## Migration Plan

1. Deploy.
2. Run `resave_all_events` on Render.

**Rollback:** revert, and re-render again.
