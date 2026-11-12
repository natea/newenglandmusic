## Context

See `proposal.md` for why. Today:

- **The site** is the Render web service `newenglandmusic`, at newenglandmusic.onrender.com. `render.yaml` leaves `SITE_URL` and `ALLOWED_HOSTS` to the dashboard (`sync: false`); `prod.py` adds the onrender hostname to `ALLOWED_HOSTS`; `healthCheckPath` is `/`.
- **The name** comes from `SITE_NAME` (default "New England Music") in the calendar feeds, the privacy page (through the `site` context processor) and the Sites record (`core/site_record.py`). It's also hard-coded in four places:
  - the masthead (`base.html`);
  - the admin's header (`admin.py`);
  - Open Graph's default title (`opengraph.py`);
  - each event's calendar entry (`Event.calendar_name`), which also becomes the feed's `SUMMARY` and the Google Calendar link's text.
- **The onrender URL** is hard-coded in `core/user_agent.py`, as the contact address the site's API clients send. Those clients run mostly in the scheduled jobs, which get no `SITE_URL` from Render: only web services get `RENDER_EXTERNAL_URL`, and `SITE_URL` otherwise falls back to localhost.
- **The share preview image** (`core/static/core/images/share-preview.png`, used for every page's Open Graph image) reads "NEW ENGLAND MUSIC". The web manifest's `name` and `short_name` are empty.
- **Calendar UIDs** end in `@` plus `UID_DOMAIN` (default "newenglandmusic"). Nate believes nobody has subscribed to the feeds (11 November 2026).
- **Saved shows** live in the first-party `saved_shows` cookie, which belongs to the host it was set on.
- **stagehopper.app** is in Cloudflare:
  - the apex's four A records (DNS only) point at GitHub Pages, serving `natea/twag`'s `docs/` (CNAME `stagehopper.app`, a legacy build from `main:/docs`, its domain not verified with GitHub);
  - www is a CNAME to natea.github.io;
  - nola. and nolajazzfest. are other repositories' Pages sites behind Cloudflare's proxy; worldcup. is a CNAME to another Render service;
  - the apex also has Cloudflare Email Routing's MX records and an SPF TXT record.
- **The landing page** is StageHopper's, run by Jazkarta, Inc. d/b/a StageHopper. Besides `index.html` it serves:
  - `privacy.html` and `terms.html`, the policy and terms of the StageHopper website and its iOS app, whose canonical links are at stagehopper.app;
  - `events_map_{boston,nyc}.html` and `events_gallery_{boston,nyc}.html`;
  - `{boston,nyc}_gallery.json` and `{boston,nyc}.geojson`;
  - `og*.png`;
  - the `boston/` and `nyc/` folders;
  - scripts, styles and `assets/`, loaded only by its own pages.
- **The site's own routes** (`core/urls.py`, and the static-page catch-all for paths ending in `/`) use no `.html`, `.json` or `.geojson` paths, and no `/boston/` or `/nyc/` pages.
- **The privacy page** (`/privacy`) is linked from every footer, as `youtube-artist-preview` requires, and says nothing about email addresses. The site stores submitters' emails (`Event.user_submission_email`) and has an `EmailSubscriber` model; the digest that will use it is a separate change.

## Goals / Non-Goals

**Goals:**
- One public name, Stagehopper, and one address, https://stagehopper.app, with every other address sending visitors there.
- Nothing outside relies on breaks: the health check, and the landing page's links (above all, the iOS app's privacy policy link).
- A terms page, and a privacy page that covers email, before the site starts asking for email addresses.

**Non-Goals:**
- Renaming the Render service, the repository or the database, and the other out-of-scope items, each with its reason, in `proposal.md`.
- Carrying visitors' saved shows across the address change (Nate, 11 November 2026: few people have any).

## Decisions

### 1. The name lives in settings, everywhere

`SITE_NAME` defaults to "Stagehopper". The four hard-coded places read it: the masthead, through the existing `site` context processor; the admin's `site_title` and `site_header`, set where the admin is configured; `opengraph.DEFAULT_TITLE`, read when called; and `Event.calendar_name`.

A new `SITE_TAGLINE` (default "Live music across New England") goes under the masthead's name as a smaller line, through the same context processor. A blank or whitespace-only value hides it. The masthead keeps `DESIGN.md`'s headline style, and the tagline uses the existing small text style, so the masthead's layout doesn't change at phone width. The web manifest's `name` and `short_name` become "Stagehopper". The share preview image needs a Stagehopper version, made as a plain text-on-colour image in the old one's layout until there's a real visual identity (task 1.5).

The spelling is "Stagehopper", as Nate wrote it. The landing page and app use "StageHopper". The spelling, like the tagline's wording, is Nate's to confirm (Open Questions).

### 2. One middleware redirects every other host, switched on by CANONICAL_HOST

A small middleware runs early, after `SecurityMiddleware`. It acts only when the new setting `CANONICAL_HOST` is set, which only production does (stagehopper.app). `SITE_URL` can't serve as the switch: it always has a value, falling back to `RENDER_EXTERNAL_URL` and then localhost. Redirecting on it would send the test client (`testserver`), the browser tests, `127.0.0.1` (which Spotify's loopback callback needs) and preview hosts to localhost.

When it acts, it reads the host with `request.get_host()` and does two things:
1. **A landing-page path** (decision 5) on the canonical host goes to the same path at https://info.stagehopper.app.
2. **A request on any other host** goes to `SITE_URL` with the same path and query, except `/health`.

GET and HEAD get a 301. Other methods get a 308, so a stale form posted to the old address keeps its method and body instead of silently becoming a GET. It will still fail Django's CSRF check, since its cookie and `Origin` belong to the old host, so the visitor submits it again on the new address. The target comes from settings only, never from the Host header.

The rule lives in code, not in Cloudflare or Render, because neither can redirect the onrender.com address: Render serves it directly. Calendar feeds get no exception, since Nate believes nobody subscribes to them (11 November 2026).

`core/user_agent.py` builds its contact address from `SITE_URL`. `render.yaml` gives both scheduled jobs `SITE_URL` from the web service (`fromService`), so they send https://stagehopper.app, not localhost. That needs the web service to have `SITE_URL` set before the merge, and a blueprint sync after it changes (decision 7, steps 1 and 6). `prod.py` adds stagehopper.app and www.stagehopper.app to the allowed hosts in code, so they're accepted from the first deploy, before DNS moves.

### 3. A dedicated health check

`/health` answers 200 with the body "ok" and reads no database. `render.yaml`'s `healthCheckPath` becomes `/health`, since `/` on the onrender address will now redirect. The old `/` check also rendered the whole home page every few seconds.

### 4. Calendar UIDs and names change

`UID_DOMAIN`'s default becomes "stagehopper", so feeds and downloads say Stagehopper throughout. Nate believes nobody has subscribed, so no calendar would show an event twice (11 November 2026).

### 5. The landing page's old paths go to info.stagehopper.app

The landing page's paths at stagehopper.app redirect to the same path at info.stagehopper.app. That covers:
- top-level `.html`, `.json` and `.geojson` files;
- `og.png`, `og_boston.png` and `og_nyc.png`;
- anything under `/boston/` and `/nyc/`.

Above all, that keeps `stagehopper.app/privacy.html`, very likely the privacy policy URL in StageHopper's App Store listing, showing StageHopper's own policy, not the music site's. Its scripts, styles and `assets/` aren't redirected: only its own pages load them, and those pages now come from info.stagehopper.app. The list is fixed in code, from the landing page's files as they are today.

### 6. Terms and privacy texts

The terms page is a new template on the site's static-page layout, as the privacy page is. It covers:
- what the site is;
- acceptable use (personal use, no bulk copying, no automated scraping beyond robots.txt);
- that listings come from venues, ticketing services and other sources, and may be wrong or change;
- that links go to other sites with their own terms;
- that the terms may change;
- the contact address.

The privacy page gains a "Your email address" section:
- event submitters' emails are used only to ask about their submission, and aren't shown publicly;
- subscribers' emails are used only for the email they signed up for, with an unsubscribe link in each one;
- who can see them: the site's editors;
- how to have one removed: write to the contact address.

Both are plain-language drafts, not reviewed by a lawyer. Nate approves the wording before the merge (task 3.4). Who runs the site, which the landing page's terms name as Jazkarta, Inc. d/b/a StageHopper, is his to state (Open Questions).

### 7. The switch, in order

Done by Nate in the dashboards, with Claude watching each step. Steps 0–3 are safe ahead of time; steps 4–6 are done together.

0. **Upgrade and back up the database, now** (Nate, 11 November 2026). The production database is on Render's free plan, which has no backups and is deleted after 30 days (`PRODUCTION.md`). This doesn't wait for the rename's review or merge:
   - **Upgrade it** in the dashboard, to `PRODUCTION.md`'s suggested `0.1c-256mb` ($10.50 a month) unless Nate picks another. Upgrading keeps the data, and paid plans add point-in-time recovery for a limited window.
   - **Dump it** with the backup command in `PRODUCTION.md`'s "Keeping the data" note: `pg_dump --format=custom "<External Database URL>" > prod-YYYY-MM-DD.dump`, run from Nate's machine. Use a `pg_dump` of version 17 or newer, since the database is Postgres 17, and allow the machine's IP under the database's Access Control if it's restricted. Don't follow the "Loading the local database" section, which ends by restoring a local database over Render's.
   - **Check the dump restores**, only ever into a local scratch database: `createdb nem_scratch && pg_restore --no-owner --dbname nem_scratch prod-YYYY-MM-DD.dump`. Never point `pg_restore` at the External Database URL. Keep the dump out of the repository, since it holds admin password hashes.

   This change alters no data beyond re-rendering stored event pages (`resave_all_events`) and the deploy's migrations, but the switch is where a mistake would be hardest to undo.
1. **Merge and deploy.** Before merging, check in the Render dashboard that `SITE_NAME` isn't already set on the web service (if it is, clear it or set it to "Stagehopper"), and set `SITE_URL=https://newenglandmusic.onrender.com` if it's blank: `render.yaml` now passes `SITE_URL` to the jobs with `fromService`, and `PRODUCTION.md` records that a blueprint sync fails at once when the web service lacks a variable a job takes from it. After merging, check that the blueprint sync succeeded, which also applies the database plan. The name changes at once at the onrender address (masthead, feeds, admin, Sites record), but no redirect runs, since `CANONICAL_HOST` isn't set. Then run `python manage.py resave_all_events` in the Shell tab, so stored event pages and their calendar links carry the new name. Also check in the admin that no static page lives at `/boston/` or `/nyc/`, the landing page's folders, which the redirect will send away.
2. **Add Render's custom domain**, stagehopper.app, under the web service's Settings > Custom Domains. Render adds www itself, and redirects www to the apex at its edge. Render waits for DNS before it verifies, and adding it first shortens the gap in step 5.
3. **Prepare the landing page's new home:**
   - verify stagehopper.app under the GitHub account's Pages settings (a TXT record in Cloudflare), so no one else can claim it while it's unclaimed in steps 4–5;
   - add `info` as a CNAME to `natea.github.io` in Cloudflare, DNS only;
   - add info.stagehopper.app to the landing page's Mapbox token's allowed URLs, and to PostHog's and Datadog's allowed origins, so its maps and analytics keep working.
4. **Move the landing page.** In `natea/twag`:
   - change the Pages custom domain to info.stagehopper.app in the repository's settings, which commits `docs/CNAME` itself (don't also edit the file);
   - move the canonical links and `og:url`s in `index.html`, `privacy.html` and `terms.html` to info.stagehopper.app;
   - wait for GitHub's certificate. `.app` is HSTS-preloaded, so browsers can't open it without one.
5. **Point DNS at Render.** Replace only the apex's four GitHub A records with Render's (its A record, or a CNAME to `newenglandmusic.onrender.com` that Cloudflare flattens), leaving the MX and SPF records alone. Repoint www to `newenglandmusic.onrender.com`. Both stay DNS only. From step 4 until Render's certificate, stagehopper.app shows an error, usually for minutes.
6. **Turn on the redirects.** Set `CANONICAL_HOST=stagehopper.app` and `SITE_URL=https://stagehopper.app` on the web service, which redeploys it. Then press **Manual Sync** on the blueprint, so the jobs get the new `SITE_URL`. Until then they would still send the onrender address.
7. **Check** (task 5.2), and add the new address to Spotify's redirect URIs for the unmerged `add-spotify-followed-artists` change.

nola. and nolajazzfest. stay behind Cloudflare's proxy, and worldcup. stays on its own Render service, all untouched. The apex and www stay DNS only.

### How outside services are mocked in tests

No outside service is called by this change. Everything is tested with Django's test client:
- the middleware, settings, templates and redirects, setting `HTTP_HOST` and overriding `CANONICAL_HOST`, `SITE_URL`, `SITE_NAME`, `SITE_TAGLINE` and `UID_DOMAIN` per test, including a test that the default settings redirect nothing;
- production's hosts, by loading `prod.py` with its environment set, as `test_prod_settings.py` already does.

DNS, Render's custom domains and GitHub Pages are checked by hand in the live check, not in tests.

## Risks / Trade-offs

- **A gap during the switch.** From moving the landing page until Render's certificate, stagehopper.app shows an error. Adding the domain first and doing steps 4–6 together, outside busy hours, keeps it short. Until step 6's redeploy finishes, the landing page's old paths, `/privacy.html` among them, also 404 at stagehopper.app, since the redirect isn't on yet. Turning it on earlier would send the onrender address into DNS that isn't ready.
- **Search engines see a 301 from the old address.** That's the intended signal, and the sitemap is built from `SITE_URL`.
- **Admin sessions and saved shows** on the old address don't carry over. Editors log in again; visitors' saved shows start empty (accepted by Nate).
- **The landing page grows new paths** after this list is fixed. Those would 404 at stagehopper.app instead of redirecting. That's harmless, since only links made before the move point there.

## Migration Plan

The steps above. Rollback before step 6 means undoing the DNS changes and the twag custom domain. After step 6, clearing `CANONICAL_HOST` turns the redirects off with one redeploy, a few minutes; then set `SITE_URL` back to the onrender address and restore the DNS.

## Open Questions

- **The tagline.** The default is "Live music across New England". Nate asked for a tagline "about New England Music". But `PRODUCT.md` says the site covers the wider Northeast, which was one reason the old name wasn't final. Confirm the wording, or pick one that covers the Northeast.
- **The spelling.** "Stagehopper", as Nate wrote it, or "StageHopper", as the landing page and app write it?
- **Who runs the site**, for the terms page. Is it Jazkarta, Inc. d/b/a StageHopper, as on the landing page's terms?
- **The terms and privacy texts** need Nate's approval as written (task 3.4).
- **Renaming the Render service, the repository or the database** later, as their own changes, if Nate wants them.
