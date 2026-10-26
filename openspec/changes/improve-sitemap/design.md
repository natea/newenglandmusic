# Design

## Context

- **Sitemap:** `core/sitemap.py` has one `Sitemap` class, which lists `/`, the static pages and one URL per month with approved events. Since `0bcc8b2` it takes its address from `SITE_URL`. Its entries come out of a `set`, so their order changes between requests.
- **Pages:** the listing pages are `index` and `past_month_archive` in `core/views/index.py`. Both go through `_get_events_page_for_month`, which applies the geo filter and its cookie.
- **Event HTML:** each event is rendered once into `Event.baked_html_template`, by `bake_event_html`, and listings show that stored HTML. A template change therefore needs `resave_all_events`.
- **Share links:** `/event/<id>` (`event_redirect`) renders `core/empty.html` with Open Graph tags and a meta refresh to `/<month>/#event-<id>`.
- **Areas:** `GeoArea` has `kind` and `slug`, unique together, and `offered_areas(kind)` lists the areas the filters offer.
- **Venues:** a venue has no slug. `is_active` is nullable, and the public listing treats anything but `False` as active.
- **URLs:** `nycnoise/urls.py` ends with a static-page catch-all, `^(?P<url_path>.*)/$`, so the new routes go in `core/urls.py`, which is included ahead of it.
- **Places terms:** `refresh-place-coordinates` (not yet applied) removes the stored Places name, address, website and phone, and builds the map link from the place ID. The site stays unshared until those terms, and the open question of which map to use, are settled.

## Goals / Non-Goals

**Goals:**
- Real, linkable pages for venues, events and areas, built from existing data and templates.
- A sitemap that lists them in a stable order with honest dates.
- Nothing invites search engines in before launch.

**Non-Goals:**
- An embedded map on venue or event pages. That waits for the map decision, and the Google Maps link covers it for now.
- Changing how the listing filters, or their cookie, work.
- Structured data (schema.org `MusicEvent` / `MusicVenue`). It would be a good follow-up once the pages exist.
- Pages for inactive venues, or redirects to them.

## Decisions

**Venue address: a stored slug, not the ID.** `/venue/paradise-rock-club-boston/` is readable and is what people and search engines see.
- **How it's made:** `Venue.slug` is a unique `SlugField`, made from name and town. A number is added on a clash, as in `-2`.
- **Existing venues:** filled in by a data migration.
- **New venues:** set when `sync_venues_from_gsheets` creates them.
- **Renames:** the slug isn't regenerated, so links survive.
- **Alternative considered:** `/venue/<id>/<slug>/`, which survives renames without a stored field. It was rejected because two-part URLs are uglier, and renames are rare.

**The event page replaces the redirect at the same address.** Every share link already in the wild then becomes a real page with no extra redirect. The Open Graph tags move into the new template's head. The Telegram delay goes away, since there's no redirect left to delay.

**Area pages share the listing code but skip the cookie.** `_get_events_page_for_month` gains a way to take an explicit filter and skip the cookie handling, so an area page and `/?state=vermont` list exactly the same events. Month links on an area page go to `/<month>/?state=vermont`, which uses the existing filter. Area slugs come from `GeoArea.slug` and are looked up by kind.

**Listings link venue names through the stored event HTML.** `event.html` links the venue name to `/venue/<slug>/`, and `resave_all_events` re-renders the stored HTML. A venue that later becomes inactive leaves a stale link in stored HTML until its events are re-rendered, so the `Venue.save()` path that already re-renders events covers that.

**Sitemap: one section per page kind.** Django's `sitemaps` dict takes several `Sitemap` classes: static, months, areas, venues and events. Each sorts its own items, and the dict's order sets the section order. Every section uses the `SITE_URL` domain and protocol through a shared base class, which is the fix from `0bcc8b2` moved up into it. Even at ~600 venues and ~600 events, we stay far below the 50,000-URL limit of one sitemap file.

**Last-modified dates come from new `updated_at` fields.** `Event.updated_at` and `Venue.updated_at` use `auto_now`. `auto_now` doesn't fire on `queryset.update()`, so each `update()` that changes what a page shows sets `updated_at` explicitly: `classify_events` doesn't need to, but the lookup and sync commands that change public venue details do. Listing-page dates are the maximum over the events they list, worked out in one aggregate query per section.

**Indexing switch: `ALLOW_SEARCH_INDEXING`**, an environment setting that defaults to off.
- **When it's off:** `/robots.txt` says `Disallow: /`, and `base.html` adds `<meta name="robots" content="noindex">`.
- **When it's on:** `/robots.txt` allows everything except `/admin/`, and the meta tag goes away.
- **Either way:** `/robots.txt` names the sitemap.
- **How it ships:** `render.yaml` and `PRODUCTION.md`'s launch checklist get the setting, off.

**Testing and external services.** None of these pages calls an external service. The tests use Django's test client against the test database, with `GeoArea`, `Venue` and `Event` rows created in the tests. The sheet-sync test for new-venue slugs uses the existing mocked `gog` output. Nothing here needs the network, and the suite still runs with outbound network blocked.

## Risks / Trade-offs

- [Venue pages expose Places data the terms don't allow.] → They show only sheet fields and a place-ID map link, and a test checks the Places address and phone don't appear.
- [The sitemap or pages get indexed before launch.] → `ALLOW_SEARCH_INDEXING` is off by default, with tests for both states.
- [Slug clashes or empty names produce bad URLs.] → Uniqueness is enforced by the database, with numbered suffixes and a fallback to the sheet ID when a name slugs to nothing.
- [Stored event HTML holds stale venue links.] → Re-render all events on release, and re-render a venue's events when its slug or active state changes.
- [Missed `update()` calls leave `updated_at` stale.] → A dated sitemap entry that's a little old is harmless. The plan lists the known `update()` sites to fix.

## Migration Plan

Each part can ship on its own, in task order. Venue pages come first, because event pages link to them. Each release:
1. Merge to `main`. Render runs the migrations: the slug, then the `updated_at` columns.
2. Run `resave_all_events` once, from the Render Shell tab, after the release that changes `event.html`.

`ALLOW_SEARCH_INDEXING` stays off until launch.

**Rollback:** revert the release. The new columns are additive and can stay.
