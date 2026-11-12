## 1. The name and tagline

- [ ] 1.1 Default `SITE_NAME` to "Stagehopper", and add `SITE_TAGLINE` (default "Live music across New England") in `nycnoise/settings/base.py`. Expose both to templates through a context processor.
- [ ] 1.2 Read `SITE_NAME` in the masthead (`base.html`, with the tagline under it), the admin's title and header, `opengraph.DEFAULT_TITLE` and `Event.calendar_name`. Keep the masthead's layout at phone width.
- [ ] 1.3 Tests for "The masthead and title", "A name from the setting", "An event's calendar entry", "The default tagline" and "No tagline".
- [ ] 1.4 Change the calendar feeds' default name, keeping `UID_DOMAIN`'s default "newenglandmusic". Tests for "Calendar name" and "UIDs survive the rename", keeping "Names from the settings", "Stable identifiers", "Cancelled event", "Window" and "Unapproved event left out" passing.

## 2. The address and redirects

- [ ] 2.1 Build `core/user_agent.py`'s contact address from `SITE_URL`. Test "The API clients' contact address".
- [ ] 2.2 Add `/health` (200, plain "ok", no database) and set `render.yaml`'s `healthCheckPath` to it. Test "The health check".
- [ ] 2.3 Add the redirect middleware after `SecurityMiddleware`: a 301 to `SITE_URL` with the same path and query for any other host, except the calendar feed, event downloads and `/health`; nothing when `SITE_URL` is unset or matches. Tests for "The old address", "The www address", "A subscribed calendar on the old address" and "Development".
- [ ] 2.4 Redirect `/privacy.html` and `/terms.html` to `/privacy` and `/terms`. Test "An old privacy link".

## 3. Terms and privacy

- [ ] 3.1 Add `/terms` on the static-page layout, and link "Terms" beside "Privacy" in the footer. Tests for "The footer" and "The terms page".
- [ ] 3.2 Add the "Your email address" section to the privacy page. Test "Email addresses on the privacy page".
- [ ] 3.3 Check both pages name the site from `SITE_NAME`, not a fixed name.
- [ ] 3.4 Show Nate both texts as rendered and get his approval of the wording before the merge.

## 4. Docs

- [ ] 4.1 Update:
  - `PRODUCT.md`: the name, the address, the tagline;
  - `PRODUCTION.md`: the custom domains, the switch's steps, `/health`, the redirect and its exceptions;
  - `.env.example`: `SITE_NAME`, `SITE_TAGLINE`;
  - `DESIGN.md`: the masthead's name and tagline;
  - the comment on `SITE_NAME` in `base.py`.
- [ ] 4.2 Run the whole suite and fix what this change broke: the tests that assert "New England Music" or the onrender address.

## 5. The switch (Nate, in the dashboards, after the merge)

- [ ] 5.1 Do the steps in `design.md` decision 7: move the landing page to info.stagehopper.app (`natea/twag`), add Render's custom domains, point Cloudflare's DNS at Render, set `SITE_URL` and `ALLOWED_HOSTS`, then run `resave_all_events`.
- [ ] 5.2 Live check:
  - https://stagehopper.app shows "Stagehopper" with the tagline;
  - www and the onrender address redirect;
  - an existing calendar subscription still updates on the old address;
  - `/privacy.html` redirects;
  - info.stagehopper.app shows the landing page with its city links;
  - nola., nolajazzfest. and worldcup.stagehopper.app still load;
  - admin login works at the new address.
- [ ] 5.3 Add `https://stagehopper.app/…` to Spotify's redirect URIs alongside the existing ones, and update the unmerged `add-spotify-followed-artists` change to use `SITE_URL`.
