## Why

A visitor browsing weeks of listings finds shows they might go to, then loses them in a list of thousands. They need a way to mark a show and come back to their picks.

## What Changes

- **A SAVE link on every event.** It sits in the event's line of links, after ICAL, GCAL, MAP and SHARE. Clicking it saves the show, and the link changes to SAVED. Clicking it again unsaves the show.
- **A "Saved shows" page at `/saved`.**
  - It lists the visitor's saved shows that are still upcoming, grouped by date like the homepage, each event looking exactly as it does in the listing.
  - It also ignores the region, state and metro filter, so a saved show never disappears because of the area the visitor is browsing.
  - A header link, "Saved shows", shows how many are saved.
- **No accounts.**
  - Saved shows live in the visitor's browser, as a cookie listing event IDs. They work at once, with no sign-up, and the site stores nothing about the visitor.
  - The trade-off: saved shows don't follow the visitor to another browser or device.
- **Tidying:** past, deleted and unapproved events drop off the page and out of the cookie, so the list keeps only shows that can still happen.
- **Not included:** grouping by venue, artist or location. The page is built so that other groupings can be added later as options, alongside the default grouping by date.

## Capabilities

### New Capabilities
- `saved-shows`: saving and unsaving events in the visitor's browser, the "Saved shows" page grouped by date, and the header link with its count.

### Modified Capabilities
None. The event listing gains a link, but no existing requirement changes.

## Impact

- **New code:**
  - a `/saved` view and template that reuse the homepage's date grouping and each event's stored HTML;
  - a small script, `saved_shows.js`, for the SAVE links and the header count;
  - a SAVE link in `event.html`;
  - a header link in `base.html`.
- **No model, migration or new dependency.**
- **Stored event HTML:** it's the same for every visitor, so whether a show is saved is set in the browser when the page loads, not baked into the stored HTML. Adding the SAVE link means re-rendering the stored events once (`resave_all_events`).
- **Tests:**
  - Django tests for the page: cookie parsing, grouping, dropping past and unapproved events, the count, ignoring the area filter;
  - Playwright browser tests for saving and unsaving, all offline.
