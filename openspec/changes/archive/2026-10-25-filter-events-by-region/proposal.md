## Why

The calendar now covers 729 venues in 12 states, from Maine to DC, and the listing shows all of them at once. Someone in Boston has to scroll past Philadelphia and Portland shows to find tonight's gigs. The venue sheet already defines the geography people browse by: regions ("New England: North", "Tri-State"), states, and metro areas ("MA: Boston Metro Region", "NY: Hudson Valley"). The Music Map's Region, State and Metro Areas dropdowns use these lists. The events listing should offer the same lists. Admins reviewing imported events need them too, so they can work through one area at a time.

## What Changes

- **The sheet's geography is synced into the database.** `sync_venues_from_gsheets` also reads the sheet's `geo-filters_json` tab, which lists every region, state and metro area. For each one, the tab gives the rule that decides which venues belong to it: a list of states, optionally narrowed by county or city. The tab's row order sets the order of the options.
- **The events listing gets three filters:** Region, State and Metro Area.
  - **Where:** on the homepage (the next three weeks) and on the month archives.
  - **How they combine:** the filters narrow each other. The Metro Area list shows only the metros of the chosen state.
  - **In the URL:** a filtered page has a shareable URL, for example `/?state=massachusetts&metro=ma-boston-metro-region`, and the month links keep the filter.
  - **What filtering changes:** the calendar, the event list and the day maps all show only matching events.
  - **Bad values:** an unknown or stale value in the URL is ignored. It never causes an error.
- **The site remembers a visitor's last filter.**
  - **What's saved:** choosing a filter saves it in a first-party cookie for a year.
  - **On a later visit:** opening `/` or a month archive with no filter in the URL redirects to the same page with the saved filter applied, so the URL always shows what's being filtered.
  - **Clearing:** setting every filter back to "All", or following the "show all" link, clears the cookie.
  - **Shared links:** a link that carries a filter wins over the cookie and becomes the new saved filter.
- **The admin gets the same Region, State and Metro Area filters** in the sidebar of both admin event lists: the events list and the all-events list at `/admin/core/alleventproxy/`. The venue list gets them too.
- **Entries the sheet can't match are hidden.** "Northeast Corridor" has no states in the sheet, so it doesn't appear as an option until the sheet gives it some.

## Capabilities

### New Capabilities

- `event-geo-filter`: filters the public events listing and the admin event and venue lists by the regions, states and metro areas defined in the venue sheet.

### Modified Capabilities

- `venue-sheet-sync`: a sync also reads the `geo-filters_json` tab and replaces the stored geography with it. A sync stays all or nothing, and a dry run previews the geography changes too.

## Impact

- **Model:** one new model, `GeoArea`, holds each region, state or metro area: its kind, sheet ID, label, URL slug, sort order and matching rules. The model needs one migration. `Venue` and `Event` don't change.
- **New code:** `core/geo_filters.py`, which turns an area's rules into a venue query and parses the filter from the URL.
- **Changed code:**
  - `sync_venues_from_gsheets`: reads the second tab.
  - `core/views/index.py`: filters events, passes the options to the template, and reads, sets and clears the filter cookie.
  - `core/templates/core/index.html`: adds the filter form, and the month links keep the filter.
  - `core/admin.py`: adds three `SimpleListFilter`s, which `EventAdmin` and `VenueAdmin` share.
- **No paid APIs.** Matching runs locally on the venue's state, county and city from the sheet, with no Google Places or Anthropic calls.
- **Sheet data to fix in the copy, not in code:**
  - The 12 DC venues have county `-`, so they miss "DC: Washington Beltway", which matches on county "District of Columbia". They still match the "DC" state and its regions.
  - The state label "Pennslyvania" is misspelled.
  - Rhode Island has no metro areas, which is expected.
- **Cookie:** one functional cookie, `geo_filter`, which holds only the chosen area slugs. It's set only after a visitor chooses a filter, and it isn't used for tracking.
- **Not breaking:** a visitor who never chooses a filter gets no cookie and sees exactly what they see today. The admin behaves as it does today until an admin picks one of the new filters.
