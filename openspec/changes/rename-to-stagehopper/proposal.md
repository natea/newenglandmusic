## Why

The site is called "New England Music" and lives at newenglandmusic.onrender.com. The name was never final: `PRODUCT.md` says it covers the wider Northeast. Nate decided on 11 November 2026 to rename it Stagehopper and serve it at https://stagehopper.app, with a New England music tagline. stagehopper.app now serves StageHopper's landing page (and the privacy policy and terms of its website and iOS app), which moves to info.stagehopper.app.

Nate also asked that the site have terms and privacy pages, since it collects email addresses: event submitters' emails today, and subscribers' for the planned email digest.

## What Changes

- **The site is named Stagehopper.** `SITE_NAME` defaults to "Stagehopper". That carries the name into:
  - the masthead, page titles and link previews (Open Graph);
  - the admin's header;
  - the calendar feeds' names ("Stagehopper: Vermont");
  - each event's calendar entry ("… [Stagehopper]");
  - the privacy and terms pages.

  The masthead gains a tagline under the name, set by `SITE_TAGLINE`, with the default "Live music across New England" (wording to confirm).
- **Its address is https://stagehopper.app.** Production sets `SITE_URL` to it, and accepts stagehopper.app, www.stagehopper.app and the onrender.com address as hosts. The contact address the site's API clients send (MusicBrainz, Wikidata, Last.fm and others) comes from `SITE_URL` instead of the hard-coded onrender address.
- **Other addresses redirect to it.** A new setting, `CANONICAL_HOST`, set only in production, switches the redirects on, so tests and development never redirect. With it set, a request to www.stagehopper.app or to the onrender.com address is redirected permanently to the same path and query at https://stagehopper.app (301, or 308 for a form submission, so it isn't lost). Only the health check is served at any address. It moves from `/` to its own `/health`, since `/` on the old address now redirects.
- **Calendar UIDs and names change too.** `UID_DOMAIN` defaults to "stagehopper". Nate said on 11 November 2026 that he doesn't think anyone has subscribed to the feeds, so no subscriber's calendar would show events twice, and feeds need no exception from the redirect.
- **Saved shows on the old address are left behind.** They live in a cookie that belongs to the old host. Nate said few people have saved shows (11 November 2026).
- **The landing page's old addresses go to its new home.** stagehopper.app served the landing page's own files: its privacy policy and terms, the Boston and New York maps and galleries, and their data and images. Those paths redirect permanently to the same path at https://info.stagehopper.app. Links in the wild, including the iOS app's privacy policy link, keep reaching StageHopper's own policy.
- **A terms page and an updated privacy page for the site.**
  - A new `/terms` page sits beside the existing `/privacy` link in every page's footer.
  - The privacy page gains a section on email addresses: what's collected (a submitter's email, a subscriber's email), why, who sees it, and how to have it removed.

  Both texts are plain-language drafts, not reviewed by a lawyer, and Nate approves their wording before the merge.
- **Hosting moves**, done by Nate in the dashboards, with the steps in `PRODUCTION.md`:
  - Render serves the web service at stagehopper.app and www.stagehopper.app as custom domains.
  - Cloudflare's DNS points those names at Render and info.stagehopper.app at GitHub Pages, as DNS-only records, as today.
  - The landing page's Pages site (`natea/twag`, `docs/`) changes its custom domain to info.stagehopper.app, and its canonical links and `og:url`s (`index.html`, `privacy.html`, `terms.html`) move with it.
  - nola., nolajazzfest. and worldcup.stagehopper.app stay as they are.
- **A backup first.** Right away, ahead of this change's merge, the production database moves off Render's free plan (no backups, deleted after 30 days) to a paid one, and is dumped. The dump is checked by restoring it into a local scratch database. `render.yaml`'s database plan changes to match (Nate, 11 November 2026).
- **After the switch**, `resave_all_events` re-renders every event, since each event stores its page's HTML with the old name in it.
- **Docs:** `PRODUCT.md` (name, address), `PRODUCTION.md` (custom domains, the redirect, the switch), `.env.example` (`SITE_NAME`, `SITE_TAGLINE`, `UID_DOMAIN`), and `DESIGN.md`'s masthead.

Out of scope, each for a reason:
- **Renaming the Render service:** that changes its onrender.com address, which the redirect, the deploy settings and the docs all rely on, for no visible gain once stagehopper.app is the address.
- **Renaming the GitHub repository:** that breaks the Spek pages' address, the intentable bridge's settings and every clone's remote, for no visible gain.
- **Renaming the database:** its name is never shown.
- **The Fabro workflow prompts and the Spek page title:** they name the project for agents, not the public site.
- **The design mocks in `.impeccable/`:** a record of past decisions.
- **A logo or new visual identity:** a design decision of its own.

Each of the first three can follow as its own change if Nate wants it (see the design's Open Questions).

## Capabilities

### New Capabilities

- `site-identity`: the site's name and tagline, its address and the redirects from its other addresses, the landing page's old paths, the health check, and the terms page and the privacy page's email section.

### Modified Capabilities

- `area-calendar-feeds`: "Feed events stay up to date in calendar apps" defaults the calendar's name to "Stagehopper" and the UID domain to "stagehopper".

## Impact

- `nycnoise/settings/base.py` and `prod.py`: `SITE_NAME`, `SITE_TAGLINE`, `UID_DOMAIN`, `CANONICAL_HOST`, the hosts.
- `render.yaml`: `healthCheckPath`, the database's paid `plan`, and `SITE_URL` passed from the web service to both scheduled jobs. `SITE_URL` and `CANONICAL_HOST` are dashboard settings (`sync: false`).
- `core/static/core/images/share-preview.png` (a Stagehopper version) and the web manifest's name.
- New middleware for the redirects.
- `core/templates/core/base.html`: the masthead and its tagline, and the footer's terms link.
- `core/templates/core/privacy.html`, and a new `core/templates/core/terms.html`.
- `core/urls.py`: `/terms` and `/health`.
- `core/admin.py`, `core/opengraph.py`, `core/models.py` (`calendar_name`) and `core/user_agent.py`.
- Tests beside each.
- Outside the repository: Render's custom domains, Cloudflare's DNS records, and the `natea/twag` Pages site, all done by Nate. Spotify's registered redirect URIs for the unmerged `add-spotify-followed-artists` change need the new address added.
