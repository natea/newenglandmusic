## Why

The end of every event is a run of small text links ("// + ICAL + GCAL + MAP + SHARE + SAVE"), set inline in the event's text. They're hard to scan, they crowd long descriptions, and SAVE only works with JavaScript.

Worse, they're part of each event's stored HTML, so every change to them means re-rendering every stored event. This change was made partly in-session before it was written up, on 2026-10-27, and this proposal records it.

## What Changes

- **Icons, not words:**
  - **Calendar file:** a calendar with a download arrow.
  - **Google Calendar:** the blue calendar used in the subscribe panel.
  - **Map:** a pin.
  - **Share:** a box with an arrow.
  - **Save:** a bookmark, filled when saved.

  Each is named by its `title`, shown on hover and read by screen readers (the icons have no text), for example "Download to your calendar (.ics)", "Map: Paradise Rock Club" or "Save show". The "+" separators go.
- **A row of their own:** the icons move out of the event's text into a row below it, above the play buttons.
- **Rendered with the page, not stored with the event:**
  - The stored HTML keeps a placeholder where the row goes, and the row is built when a page is rendered.
  - Changing the icons no longer needs `resave_all_events`.
  - The icons are defined once per page, as SVG symbols, so each row is a few short references rather than about 1.5 KB of drawing.
- **Saving without JavaScript:**
  - The bookmark is a small form button. Without JavaScript, it posts to `/saved/toggle/<id>`, which updates the `saved_shows` cookie and returns the visitor to the same event.
  - The page shows each bookmark filled or outlined from the visitor's cookie, so saved state is right before any script runs.
  - With JavaScript, saving still happens at once, in place.
- **The search page** shows the same row, by using the stored HTML like the other listings.

## Capabilities

### New Capabilities
- `event-action-icons`: each event's row of link icons, their names, where it sits, and that it's built at page time.

### Modified Capabilities
- `saved-shows`: saving is a bookmark icon instead of a SAVE/SAVED text link, and works without JavaScript. `add-saved-shows` adds this capability and isn't archived yet, so this change must be archived after it.

## Impact

- **New code:**
  - `core/event_actions.py`, which builds the row;
  - a template tag, `event_html`, that fills the placeholder, used by the homepage, archive, Saved shows and search templates;
  - `core/templates/core/icons.html`, the SVG symbols, included in `base.html`;
  - the `/saved/toggle/<id>` view.
- **Changed:**
  - `event.html`, where the inline links are replaced by the placeholder;
  - `saved_shows.js`, which works on the bookmark button and no longer reveals a hidden link;
  - the styles.
- **Rolling out:** one last `resave_all_events`, locally and on Render, so stored events carry the placeholder. After that, changes to the icon row need no re-render.
- **Page-time cost:** building about 1,000 rows on each listing page. It's measured in the tasks, against the old stored-only page.
