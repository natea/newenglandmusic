## 0. The database, now (Nate, before the review finishes)

- [ ] 0.1 Upgrade the production database to a paid plan in the dashboard, `0.1c-256mb` unless Nate picks another. Dump it with `PRODUCTION.md`'s backup command (`pg_dump` 17+), and check the dump restores into a local scratch database, never the External Database URL (design decision 7, step 0).

## 1. The name and tagline

- [ ] 1.1 In `nycnoise/settings/base.py`:
  - default `SITE_NAME` to "Stagehopper";
  - add `SITE_TAGLINE`, defaulting to "Live music across New England";
  - default `UID_DOMAIN` to "stagehopper";
  - add `CANONICAL_HOST`, empty by default.

  Expose the tagline to templates through the existing `site` context processor.
- [ ] 1.2 Read `SITE_NAME` in the masthead (`base.html`, with the tagline under it), the admin's title and header, `opengraph.DEFAULT_TITLE` and `Event.calendar_name`. Keep the masthead's layout at phone width.
- [ ] 1.3 Tests for "The masthead and title", "A name from the setting", "An event's calendar entry", "The default tagline" and "No tagline".
- [ ] 1.4 Tests for "Calendar name" and "Default names", against the real defaults rather than an override. Keep "Names from the settings", "Stable identifiers", "Cancelled event", "Window" and "Unapproved event left out" passing.
- [ ] 1.5 Make a Stagehopper share preview image in the old one's layout, and set the web manifest's `name` and `short_name`. Check the Open Graph tags point at the new image.

## 2. The address and redirects

- [ ] 2.1 Build `core/user_agent.py`'s contact address from `SITE_URL`. Give both scheduled jobs in `render.yaml` `SITE_URL` from the web service. Add stagehopper.app and www.stagehopper.app to production's hosts in `prod.py`. Tests for "The API clients' contact address" and "Production's hosts".
- [ ] 2.2 Add `/health` (200, body "ok", no database) and set `render.yaml`'s `healthCheckPath` to it. Test "The health check".
- [ ] 2.3 Add the redirect middleware after `SecurityMiddleware`, acting only when `CANONICAL_HOST` is set. For any other host except `/health`, redirect to `SITE_URL` with the same path and query: 301 for GET and HEAD, 308 otherwise, with the target built from settings only. Tests for "The old address", "The www address", "A calendar feed on the old address", "A form posted to the old address" and "No canonical host".
- [ ] 2.4 In the same middleware, redirect the landing page's paths on the site's own host to the same path at https://info.stagehopper.app: top-level `.html`, `.json` and `.geojson`; `og.png`, `og_boston.png` and `og_nyc.png`; anything under `/boston/` and `/nyc/`. Tests for "The landing page's privacy policy", "A landing map" and "The site's own privacy page".
- [ ] 2.5 Set `render.yaml`'s database `plan` to the paid plan's exact Blueprint name, as the dashboard shows it after 0.1, so a blueprint sync doesn't move it back to free.

## 3. Terms and privacy

- [ ] 3.1 Add `/terms` on the static-page layout, and link "Terms" beside "Privacy" in the footer. Tests for "The footer" and "The terms page".
- [ ] 3.2 Add the "Your email address" section to the privacy page. Test "Email addresses on the privacy page".
- [ ] 3.3 Name the site from `SITE_NAME` on both pages. Test "Both pages follow the setting".
- [ ] 3.4 Show Nate both texts as rendered, with who runs the site filled in as he says, and get his approval of the wording before the merge.

## 4. Docs and the suite

- [ ] 4.1 Update:
  - `PRODUCT.md`: name, address, tagline;
  - `PRODUCTION.md`: custom domains (noting that `prod.py` already allows stagehopper.app and www), the switch's steps, `/health`, the redirects, the database's paid plan and backup;
  - `.env.example`: `SITE_NAME`, `SITE_TAGLINE`, `UID_DOMAIN`, `CANONICAL_HOST`, and the install-banner comment;
  - `DESIGN.md`: the masthead's name and tagline;
  - the comments on `SITE_NAME` and `UID_DOMAIN` in `base.py`.
- [ ] 4.2 Run the whole suite and update the tests this change breaks. Known ones, which assert "New England Music", the old UID domain or the onrender address:
  - `test_calendar_feeds.py`, whose `DEFAULTS` override pins the old name;
  - `test_event_calendar_links.py`, `test_opengraph.py`, `test_band_pages.py`, `test_index_page.py`;
  - `test_site_record.py`, `test_site_settings.py`, `test_prod_settings.py`, `test_youtube_client.py`.

## 5. The switch (Nate, in the dashboards, around the merge)

- [ ] 5.1 Do the steps in `design.md` decision 7, in order: check `SITE_NAME` isn't set and set `SITE_URL` to the onrender address before the merge; deploy, check the blueprint sync, resave and check no static page at `/boston/` or `/nyc/`; add Render's custom domain; verify the domain with GitHub, add `info`, and allow it for Mapbox, PostHog and Datadog; move the landing page; point the apex's A records and www at Render; set `CANONICAL_HOST` and `SITE_URL`, then press Manual Sync for the jobs.
- [ ] 5.2 Live check:
  - https://stagehopper.app shows "Stagehopper" with the tagline;
  - www and the onrender address redirect;
  - `/health` answers on the onrender address;
  - `stagehopper.app/privacy.html` reaches StageHopper's policy at info.stagehopper.app;
  - info.stagehopper.app shows the landing page with its city links, and its Boston map loads;
  - nola., nolajazzfest. and worldcup.stagehopper.app still load;
  - admin login works at the new address;
  - a scheduled job's user agent names https://stagehopper.app (from its next run's log, or a one-off run).
- [ ] 5.3 Add `https://stagehopper.app/…` to Spotify's redirect URIs alongside the existing ones, and update the unmerged `add-spotify-followed-artists` change to use `SITE_URL`.
