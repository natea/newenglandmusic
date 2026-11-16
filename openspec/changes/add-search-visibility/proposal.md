## Why

The site can be shared now, and people look for what it lists by searching: "concerts in Portland Maine this weekend", "Paradise Rock Club shows", "Belly tour". Today search engines get little help finding or reading it:

- **`/robots.txt` is a 404.** It's caught by the trailing-slash redirect and then the static-page lookup, so crawlers don't find the sitemap from it.
- **The sitemap has no dates, and misses pages.** It lists 3,768 pages (bands, artists, months, the home page) with no last-modified dates, so a crawler can't tell what changed. It lists every month with an event, as far out as 2030. Once event and venue pages exist (`add-event-pages`, `add-venue-pages`, which this change builds on), it lists neither.
- **No canonical links.** The home page answers at many filter and cookie variants, and the pages' own share tags point act pages at an address with a trailing slash (`/bands/belly/`) that only redirects.
- **No structured data.** Google shows events, with date and venue, in its results only for pages that mark them up as events (schema.org `MusicEvent`). Nothing is marked up.
- **The default description is out of date.** It still says "New England and the Northeast".
- **No measurement.** The site isn't verified in Google Search Console, so nobody can see what it's found for, what isn't indexed, or why.

[OpenSEO](https://openseo.so) is an open-source (MIT) SEO workbench, hosted or self-hosted. It provides a site audit crawler, keyword research, rank tracking, backlinks, AI-answer visibility and reports, using DataForSEO data, and it reads Google Search Console. Hosted, it costs $10 a month including $10 of usage (1,000 credits = $1); site audits without Lighthouse or JavaScript rendering, and Search Console reads, use no credits. It has an MCP server (`app.openseo.so/mcp`) and skills this workspace already has as a plugin. It is a tool we use *on* the site, not code we put *in* it. So this change does two things: it fixes what makes the site hard to crawl and read, and it sets up OpenSEO and Search Console to measure the result and find what to fix next.

## What Changes

- **`/robots.txt` is served.**
  - It allows crawling and names the sitemap.
  - It keeps crawlers out of the admin, the email-digest pages, search results, and the per-event calendar downloads (`/event/<id>/ics`, `/event/<id>/gcal`).
- **Every public page has a canonical link** to its one address on `SITE_URL`:
  - with no query string or cookie variant;
  - with the address the page answers at without redirecting, so act pages carry no trailing slash.

  The share tags' `og:url` uses the same address, which fixes the act pages' redirecting `og:url`.
- **Structured data (JSON-LD), from data we may publish:**
  - the home page: `WebSite`;
  - act pages: `MusicGroup` for bands and `Person` for artists, with their upcoming shows as `MusicEvent`s and `sameAs` links to their own website, MusicBrainz, Wikidata, Wikipedia, Bandcamp and Instagram;
  - event pages: `MusicEvent`, with its time, venue (`MusicVenue`, using the sheet's address), performers, ticket offer and status;
  - venue pages: `MusicVenue`, with its upcoming shows as `MusicEvent`s.

  Nothing from Google Places, Last.fm, Spotify or Apple Music goes into it.
- **The sitemap gets dates and loses far-off months.**
  - It becomes a sitemap index of sections: pages, months, acts, events and venues, so each file stays small and the sections can grow.
  - It adds the upcoming event pages and the active New England venue pages.
  - Act, event and venue entries carry a last-modified date.
  - Months are listed only up to 12 months ahead.
- **The default description says New England only.**
- **Measurement, set up once:**
  - **Google Search Console:** the `stagehopper.app` domain is verified by a DNS TXT record in Cloudflare, and the sitemap is submitted. Bing Webmaster Tools imports it from Search Console.
  - **OpenSEO:** a hosted account ($10 a month) is set up as a project for `stagehopper.app` and connected to Search Console, and four things are run on it:
    - a baseline site audit (no credits, without Lighthouse or JavaScript rendering, which the server-rendered pages don't need);
    - keyword research for a starting list of New England live-music searches;
    - a small rank-tracking list;
    - an AI-visibility check of the same searches.

    The findings go into a dated report in `docs/seo/`, and each fix becomes an issue or a follow-up change.
  - **Monthly from then on:** a re-audit and a ranking check with OpenSEO's report, by hand at first, within the plan's included $10 unless the owner raises it.

## Capabilities

### New Capabilities
- `search-visibility`: what the site tells crawlers: `robots.txt`, canonical links, structured data and its sources, and the sitemap's shape, dates and range.

### Modified Capabilities
- `band-pages`: "Act pages are found by search engines" adds the act pages' canonical address and structured data.
- `event-pages` and `venue-pages` (from `add-event-pages` and `add-venue-pages`): their pages carry structured data and are listed in the sitemap.

## Impact

- **Code:**
  - a `robots.txt` view, routed ahead of the slash redirect and the static-page catch-all;
  - `core/opengraph.py` (`get_meta` builds the canonical URL without the trailing slash it adds now, and the new default description);
  - `core/templates/core/base.html` (the canonical link and a JSON-LD block);
  - a new `core/structured_data.py` that builds the JSON-LD from models;
  - `core/views/act_page.py`, and the event and venue page views;
  - `core/sitemap.py`, split into sections under an index in `nycnoise/urls.py`.
- **Migrations:** `updated_at` on `Band`, `Artist`, `Event` and `Venue`, for the sitemap's dates. Code that changes them with `queryset.update()` sets them itself.
- **Outside services:**
  - **Google Search Console and Bing Webmaster Tools:** free; verification is a DNS TXT record, with no code or meta tag.
  - **OpenSEO:** hosted at app.openseo.so, $10 a month including $10 of usage. **Keyword research, rank tracking and AI-visibility checks spend credits**; the owner approves each until their cost is known. Plain site audits and Search Console reads are free. The OpenSEO plugin's MCP tools need the owner to sign in first. Self-hosting (Docker or Cloudflare) is possible but needs its own server and DataForSEO account, so it isn't proposed.
- **Terms:**
  - Structured data uses only the sheet's venue details, never Google Places data (the Places terms).
  - It uses no Last.fm data (which needs written approval to show) and no Spotify or Apple Music metadata (their terms limit it to their own players).
  - A Wikipedia bio stays credited and isn't copied into JSON-LD.
- **Order:** `add-event-pages` and `add-venue-pages` are built and archived first; this change assumes their pages exist.
- **Relation to `improve-sitemap`:** that change predates the shareable site and the separate event and venue page changes. Its venue and event pages are now `add-venue-pages` and `add-event-pages`, and its "don't index until launch" setting no longer applies. This change takes over its `robots.txt` and sitemap-shape work. `improve-sitemap` should be revised to keep only the area pages (`/state/<slug>/`, `/metro/<slug>/`), which then join the sitemap as another section.
