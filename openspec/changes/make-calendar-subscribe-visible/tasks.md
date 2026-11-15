Issue: [#15 Incorporate the Google Calendar Simple API to generate calendars that people can subscribe to](https://github.com/natea/newenglandmusic/issues/15)

## 1. Listing

- [ ] 1.1 Rework `calendar_subscribe.html` into a visible "Subscribe" button with the same panel (webcal link, Google link, copyable address, refresh note), still a `<details>` that works without JavaScript; keep the `calendarLink` and `google` classes the analytics script listens for; verify it renders for a chosen area and for none.
- [ ] 1.2 Move the include in `index.html` to the top of the `content` block, before the area filter include, and restyle it in the stylesheet; verify the homepage and a month archive page both show it before the filter form.
- [ ] 1.3 Rewrite the two assertions in `core/tests/test_calendar_feeds.py` on the old "Subscribe to this calendar" wording, and add tests for the `area-calendar-feeds` scenarios: the button is before the filter in the page, the links for Vermont and for no area, the button on a month archive page, the panel being a `<summary>` that works without JavaScript, and the links keeping the `calendarLink` and `google` classes.

## 2. Venue pages (after `add-venue-pages` is built)

- [ ] 2.1 Pass `subscribe_links` for the venue's state from the venue page view, by looking up the offered state area for the venue's two-letter code and building a `GeoFilter` from it (`subscribe_links` unchanged), falling back to an empty filter when the state is blank or not an offered area; include the button in the venue template with a label naming the area.
- [ ] 2.2 Add tests for the `venue-pages` scenarios: a Massachusetts venue's button points at the Massachusetts feed and says so, and a venue with no state, or a state that is not an offered area, falls back to the all-areas feed.

## 3. Finish

- [ ] 3.1 Check the listing and a venue page at 390px and 1440px, with the panel closed and open, and fix overflow or overlap. Locally `webcal://` over plain HTTP does not work (see `PRODUCTION.md`), so check the links' text there.
- [ ] 3.2 Run the whole suite with the network blocked and verify it passes, with every scenario in this change's specs covered.
- [ ] 3.3 Update `DESIGN.md` for the button and its placement, and the `PRODUCTION.md` paragraph about the panel under the area filter, and verify both describe the shipped behavior.
- [ ] 3.4 Archive this change only after `add-venue-pages` is archived.
