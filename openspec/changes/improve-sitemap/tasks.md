# Tasks

## 1. Venue pages

- [ ] 1.1 Add a unique `Venue.slug`, made from name and town with numbered suffixes on a clash, and a data migration that fills it in for existing venues. Verify: `makemigrations --check` is clean after the migration, and every venue in the local database has a distinct slug.
- [ ] 1.2 Set the slug when `sync_venues_from_gsheets` creates a venue, and never change it on update or rename. Verify: tests for the "Two venues with the same name" and "Renamed venue" scenarios, using the existing mocked `gog` output.
- [ ] 1.3 Add the venue page view, template and `/venue/<slug>/` route ahead of the static-page catch-all: the sheet's public details, a Google Maps link from the place ID (or name and town), and upcoming approved events. Verify: tests for the "Venue with upcoming shows", "Venue with no upcoming shows", "Inactive venue", "Private fields stay private" and "Matched venue" scenarios.
- [ ] 1.4 Link the venue name in `event.html` to the venue page when the venue is active. Re-render a venue's events when its slug or active state changes. Verify: a test for the "Event in the home page listing" scenario, and `resave_all_events` runs locally without errors.

## 2. Event pages

- [ ] 2.1 Replace `event_redirect` with an event page view and template at `/event/<id>`, keeping the Open Graph tags and handling a missing User-Agent. Verify: tests for the "Approved event", "Unapproved event", "Past or cancelled event", "Link preview" and "No User-Agent" scenarios. The existing redirect tests are updated or removed.

## 3. Area pages

- [ ] 3.1 Let `_get_events_page_for_month` take an explicit area filter and skip the cookie handling. Add the `/region/<slug>/`, `/state/<slug>/` and `/metro/<slug>/` routes and view, with the area's name in the title and heading. Verify: tests for the "State page", "Metro page", "Unknown area", "Area of the wrong kind" and "Visitor with a remembered filter" scenarios. The existing `event-geo-filter` tests still pass.

## 4. Sitemap and indexing

- [ ] 4.1 Add `Event.updated_at` and `Venue.updated_at` with `auto_now`, and set them explicitly in the `queryset.update()` calls that change what a venue or event page shows. Verify: a migration exists, and a test confirms an admin edit moves `updated_at`.
- [ ] 4.2 Split the sitemap into static, month, area, venue and event sections on a shared base that uses `SITE_URL`, each sorted, with last-modified dates. Verify: tests for the "All page kinds listed", "Hidden pages left out", "Months in order" and "Edited event" scenarios. The existing `test_sitemap` still passes.
- [ ] 4.3 Add the `ALLOW_SEARCH_INDEXING` setting (off by default), a `/robots.txt` view, and the no-index meta tag in `base.html`. Add the setting to `render.yaml` and to `PRODUCTION.md`'s launch checklist. Verify: tests for the "Before launch" and "After launch" scenarios.

## 5. Release

- [ ] 5.1 Run the full suite with outbound network blocked, then check the new pages by hand on the local dev server: a venue, an event, a state and a metro page, and `/sitemap.xml` and `/robots.txt`. Verify: every test passes, and each page returns 200 with the expected content.
- [ ] 5.2 With the user's go-ahead, push to `main`, run `resave_all_events` on Render after deploy, and check the live sitemap lists the new pages at the `onrender.com` address with `robots.txt` disallowing all. Verify: the live checks pass.

## Workflow follow-up

- Archive with `/opsx:archive improve-sitemap` once every task is checked.
- At launch, turn on `ALLOW_SEARCH_INDEXING`, after the Google Places terms are met.
