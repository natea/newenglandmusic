## Why

The site is called "New England Music" and lives at newenglandmusic.onrender.com. That name was never final: `PRODUCT.md` says it covers the wider Northeast. Nate decided on 11 November 2026 to rename it Stagehopper and serve it at https://stagehopper.app, with a New England music tagline. stagehopper.app now serves Stagehopper's landing page, which moves to info.stagehopper.app.

Nate also asked that the site keep a privacy page and gain a terms page, since it collects email addresses: event submitters' emails today, and subscribers' for the planned email digest.

## What Changes

- **The site is named Stagehopper.** `SITE_NAME` defaults to "Stagehopper". That carries the name into:
  - the masthead, page titles and link previews (Open Graph);
  - the admin's header;
  - the calendar feeds' names ("Stagehopper: Vermont");
  - each event's calendar entry ("… [Stagehopper]");
  - the privacy page.

  The masthead gains a tagline under the name, set by `SITE_TAGLINE`, with the default "Live music across New England".
- **Its address is https://stagehopper.app.** Production sets `SITE_URL` to it, and `ALLOWED_HOSTS` takes stagehopper.app and www.stagehopper.app. The contact address the site's API clients send (MusicBrainz, Wikidata, Last.fm and others) comes from `SITE_URL` instead of the hard-coded onrender address.
- **Other addresses redirect to it.** A request to www.stagehopper.app or to the service's onrender.com address is redirected permanently (301) to the same path and query at https://stagehopper.app. There are two exceptions:
  - calendar feeds and single-event downloads are served at any allowed address, so existing subscriptions keep working without a calendar app having to follow a redirect;
  - the health check is served directly. It moves from `/` to its own `/health`, since `/` on the old address now redirects.
- **Calendar UIDs don't change.** `UID_DOMAIN` stays "newenglandmusic", because a new UID domain would make every subscribed calendar show each show twice.
- **The landing page's old pages redirect.** `/privacy.html` and `/terms.html`, which stagehopper.app served for the landing page, redirect to the site's own `/privacy` and `/terms`.
- **A terms page and an updated privacy page.**
  - A new `/terms` page sits beside `/privacy` in every page's footer.
  - The privacy page gains a section on email addresses: what's collected (a submitter's email, a subscriber's email), why, who sees it, and how to have it removed.

  Both texts are drafted for Nate to approve before they go live.
- **Hosting moves**, done by Nate in the dashboards, with the steps in `PRODUCTION.md`:
  - Render serves the web service at stagehopper.app and www.stagehopper.app as custom domains.
  - Cloudflare's DNS points those two names at Render and info.stagehopper.app at GitHub Pages, as DNS-only records while Render issues certificates.
  - The landing page's GitHub Pages site (`natea/twag`, `docs/`) changes its custom domain to info.stagehopper.app, and its links to `https://stagehopper.app/` change to the new address.
  - nola., nolajazzfest. and worldcup.stagehopper.app are left as they are.
- **After the switch**, `resave_all_events` re-renders every event, since each event stores its page's HTML with the old name in it.
- **Docs:** `PRODUCT.md` (name, address), `PRODUCTION.md` (custom domains, the redirect, the old address), `.env.example` (`SITE_NAME`, `SITE_TAGLINE`), and `DESIGN.md`'s masthead.

Out of scope:
- renaming the GitHub repository, the Render service or the database;
- the Fabro workflow prompts and the Spek page title, which name the project, not the public site;
- the design mocks in `.impeccable/`, which are a record of past decisions;
- a logo or new visual identity.

## Capabilities

### New Capabilities

- `site-identity`: the site's name and tagline, its address, redirects from its other addresses, and its privacy and terms pages.

### Modified Capabilities

- `area-calendar-feeds`: "Feed events stay up to date in calendar apps" defaults the calendar's name to "Stagehopper", keeping the UID domain "newenglandmusic".

## Impact

- `nycnoise/settings/base.py` and `prod.py`: `SITE_NAME`, `SITE_TAGLINE`, the hosts.
- `render.yaml`: `SITE_URL`, `ALLOWED_HOSTS` and `healthCheckPath`.
- New middleware for the redirects.
- `core/templates/core/base.html`: the masthead and its tagline, and the footer's terms link.
- `core/templates/core/privacy.html`, and a new `core/templates/core/terms.html`.
- `core/urls.py`: `/terms`, and the two old landing-page addresses.
- `core/admin.py`, `core/opengraph.py`, `core/models.py` (`calendar_name`) and `core/user_agent.py`.
- Tests beside each.
- Outside the repository: Render's custom domains, Cloudflare DNS records, and the `natea/twag` Pages site, all done by Nate. Spotify's registered redirect URIs for the unmerged `add-spotify-followed-artists` change need the new address added.
