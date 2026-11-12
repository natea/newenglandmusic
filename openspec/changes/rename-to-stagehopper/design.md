## Context

See `proposal.md` for why. Today:

- **The site** is the Render web service `newenglandmusic`, at newenglandmusic.onrender.com. `render.yaml` leaves `SITE_URL` and `ALLOWED_HOSTS` to the dashboard (`sync: false`); `prod.py` adds the onrender hostname to `ALLOWED_HOSTS`; `healthCheckPath` is `/`.
- **The name** comes from `SITE_NAME` (default "New England Music") in the calendar feeds, the privacy page and the Sites record (`core/site_record.py`). It's also hard-coded in five places:
  - the masthead (`base.html`);
  - the admin's header (`admin.py`);
  - Open Graph's default title (`opengraph.py`);
  - each event's calendar entry (`Event.calendar_name`);
  - the API clients' contact address (`user_agent.py`, which also hard-codes the onrender URL).
- **Calendar UIDs** end in `@` plus `UID_DOMAIN` (default "newenglandmusic"), kept apart from `SITE_NAME` on purpose.
- **Saved shows** live in the first-party `saved_shows` cookie, which belongs to the host it was set on.
- **stagehopper.app** is in Cloudflare (DNS only):
  - the apex's A records point at GitHub Pages, serving `natea/twag`'s `docs/` (CNAME `stagehopper.app`);
  - www is a CNAME to natea.github.io;
  - nola., nolajazzfest. and worldcup. are other repositories' Pages sites.
- The landing page's `index.html` has a canonical link and `og:url` of `https://stagehopper.app/`, and links the city sites.
- **The privacy page** (`/privacy`) is linked from every footer, as YouTube's developer policies ask, and says nothing about email addresses. The site stores submitters' emails (`Event.user_submission_email`) and has an `EmailSubscriber` model; the digest that will use it is a separate change.

## Goals / Non-Goals

**Goals:**
- One public name, Stagehopper, and one address, https://stagehopper.app, with every other address sending visitors there.
- Nothing that subscribers or outside services rely on breaks: calendar feeds, calendar UIDs, the health check, old landing-page links.
- A terms page, and a privacy page that covers email, before the site starts asking for email addresses.

**Non-Goals:**
- Renaming the repository, the Render service, the database or the Fabro prompts.
- A new visual identity.
- Carrying visitors' saved shows across the address change (see Open Questions).

## Decisions

### 1. The name lives in settings, everywhere

`SITE_NAME` defaults to "Stagehopper". The five hard-coded places read it, through a context processor for templates:
- the masthead;
- the admin's `site_title` and `site_header`, set where the admin is configured;
- `opengraph.DEFAULT_TITLE`, read when called;
- `Event.calendar_name`;
- `user_agent`.

A new `SITE_TAGLINE` (default "Live music across New England") goes under the masthead's name as a smaller line. A blank or whitespace-only value hides it. The tagline wording is Nate's to confirm (Open Questions).

The masthead is the `DESIGN.md` headline style. The tagline uses the existing small text style, so the masthead's layout doesn't change at phone width. Checked against `DESIGN.md`'s masthead rules when building.

### 2. One middleware redirects every other host

A small middleware runs early, after `SecurityMiddleware`. It compares the request's host with `SITE_URL`'s, and returns a 301 to `SITE_URL` with the same path and query when they differ. It skips:
- `calendar.ics` and `event/<id>/ics`. Calendar apps handle redirects unevenly, and Google Calendar is known to drop a feed that moves.
- `/health`.
- any request when `SITE_URL` is unset or its host is the request's.

So development and tests behave as now. The rule lives in code, not in Cloudflare or Render, because the onrender.com address can't be redirected by either: Render serves it directly.

### 3. A dedicated health check

`/health` answers 200 with a plain "ok" and touches no database. `render.yaml`'s `healthCheckPath` becomes `/health`, since `/` on the onrender address will now redirect. The old `/` check also rendered the whole home page every few seconds.

### 4. UIDs keep their domain

`UID_DOMAIN`'s default stays "newenglandmusic". The spec says so, with a scenario, so a later tidy-up doesn't "fix" it and double every subscriber's calendar.

### 5. Old landing-page pages

`/privacy.html` and `/terms.html` get permanent redirects to `/privacy` and `/terms`. They were the only content paths the landing page served besides `/`. Its other files (images, scripts) aren't linked from outside.

### 6. Terms and privacy texts

The terms page is a new template on the site's static-page layout, as the privacy page is. It covers:
- what the site is;
- acceptable use (personal use, no bulk copying, no automated scraping beyond robots.txt);
- that listings come from venues, ticketing services and other sources and may be wrong or change;
- that links go to other sites with their own terms;
- that the terms may change;
- the contact address.

The privacy page gains a "Your email address" section:
- event submitters' emails, used only to ask about their submission, and not shown publicly;
- subscribers' emails, used only for the email they signed up for, with an unsubscribe link in each one;
- who can see them (the site's editors);
- how to have one removed (write to the contact address).

Both are drafted in the change and need Nate's approval before merge (task 3.4). They are plain-language notices, not reviewed by a lawyer, and the proposal says so.

### 7. The switch, in order

Done by Nate in the dashboards, with Claude watching each step. Steps 1–3 can come first without breaking anything:

1. **Merge and deploy.** Nothing changes yet: `SITE_URL` is still the onrender address, so the middleware redirects only www and other stray hosts.
2. **Move the landing page.** In `natea/twag`:
   - set `docs/CNAME` to `info.stagehopper.app`;
   - change the canonical link and `og:url` to `https://info.stagehopper.app/`;
   - set the Pages custom domain.

   In Cloudflare, add `info` as a CNAME to `natea.github.io`, DNS only. Wait for GitHub's certificate. From now until step 4, the apex shows GitHub's 404, so steps 2–4 are done together.
3. **Add Render's custom domains.** stagehopper.app and www.stagehopper.app, under the web service's Settings > Custom Domains.
4. **Point DNS at Render**, DNS only:
   - replace the apex's four GitHub A records with what Render shows (its A record, or a CNAME to `newenglandmusic.onrender.com` flattened by Cloudflare);
   - repoint www to `newenglandmusic.onrender.com`.

   Wait until Render shows both domains verified with certificates.
5. **Switch the settings.** Set `SITE_URL=https://stagehopper.app` and `ALLOWED_HOSTS=stagehopper.app,www.stagehopper.app`, which redeploys. The redirects now run.
6. **Re-render** with `python manage.py resave_all_events` in the Shell tab, so stored event pages carry the new name.
7. **Check** the live list (task 5.2), and add the new address to Spotify's redirect URIs for the unmerged `add-spotify-followed-artists` change.

Cloudflare's proxy stays off (grey cloud) throughout, as today. Turning it on later needs Render's "full (strict)" TLS setting, and is out of scope.

### How outside services are mocked in tests

No outside service is called by this change. The middleware, settings, templates and redirects are tested with Django's test client, setting `HTTP_HOST` and overriding `SITE_URL`, `SITE_NAME` and `SITE_TAGLINE` per test. DNS, Render's custom domains and GitHub Pages are checked by hand in the live check, not in tests.

## Risks / Trade-offs

- **Saved shows on the old address are left behind.** The cookie belongs to newenglandmusic.onrender.com. The site hasn't been shared publicly (`PRODUCT.md`), so few people have any. Carrying them over is in Open Questions.
- **A gap during the switch.** Between moving the landing page and Render's certificate, stagehopper.app shows an error for minutes to an hour. Doing steps 2–5 together, outside busy hours, keeps it short.
- **Search engines see a 301 from the old address.** That's the intended signal, and the sitemap is built from `SITE_URL`.
- **Admin sessions end.** Logged-in editors log in again at the new address.

## Migration Plan

The steps above. Rollback before step 5 is undoing the DNS changes. After step 5, it's setting `SITE_URL` back to the onrender address, which turns the redirects off, then restoring the DNS.

## Open Questions

- **The tagline's wording.** The default is "Live music across New England". Nate said a tagline "about New England Music": confirm the wording, or give another.
- **Saved shows.** Should visitors' saved shows carry over? One way: the redirect from the old address passes the cookie's IDs once in a query parameter, and the new address merges them into its cookie. That's small, but it adds code to a path that only matters for a few weeks. This proposal leaves it out.
- **The terms and privacy texts** need Nate's approval as written (task 3.4).
