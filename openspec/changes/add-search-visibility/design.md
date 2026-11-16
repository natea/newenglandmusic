## Context

- **Share tags:** `core/opengraph.py` `get_meta()` builds them with django-meta; its `url` gets a trailing slash appended (`f"{url}/"`), which suits month pages (`/2026-11/`) but not act pages (`/bands/belly`).
- **`/robots.txt`:** no route, so `APPEND_SLASH` redirects it to `/robots.txt/`, which the static-page catch-all answers with 404.
- **The sitemap:** `core/sitemap.py` is one `SiteSitemap` of URL strings, using `META_SITE_DOMAIN` and `META_SITE_PROTOCOL`. On 2026-11-16 it listed 3,768 URLs, with no `lastmod`.
- **Pages:**
  - act pages are live (`band-pages`); this change assumes event pages (`/event/<id>`, `add-event-pages`) and venue pages (`add-venue-pages`) are built, with their own canonical links;
  - every address on another host (`www`, the onrender.com address) already redirects 301 to `https://stagehopper.app` (`site-identity`).
- **Hosting and accounts:** DNS for `stagehopper.app` is on Cloudflare, reachable through the Cloudflare connector. The OpenSEO plugin is installed in this workspace, but its MCP tools need the owner to sign in.

## Goals / Non-Goals

**Goals:**
- every public page crawlable from `robots.txt` and the sitemap, with one canonical address;
- events and acts readable as structured data;
- a measured baseline in Search Console and OpenSEO, and a monthly loop to act on it.

**Non-Goals:**
- new kinds of page (area pages stay in `improve-sitemap`; event and venue pages in their own changes);
- link building or outreach;
- paid search;
- self-hosting OpenSEO;
- automating OpenSEO from the site's cron jobs (not until the cost per run is known).

## Decisions

### 1. `robots.txt` is a view, routed first
`/robots.txt` is a plain-text view in `nycnoise/urls.py`, ahead of everything else, so neither the slash redirect nor the catch-all sees it. It returns:

```
User-agent: *
Disallow: /admin/
Disallow: /digest
Disallow: /search
Disallow: /event/*/ics
Disallow: /event/*/gcal
Disallow: /internal-api/
Sitemap: https://stagehopper.app/sitemap.xml
```

The sitemap URL comes from `SITE_URL`. AI crawlers aren't singled out: being cited in AI answers is part of what OpenSEO's AI-visibility report measures, and the content is public listings.

*Alternative:* a static file served by WhiteNoise. Rejected: the sitemap line has to follow `SITE_URL`.

### 2. One canonical address per page
`get_meta()` takes the page's path as it is served (`request.path`), keeps it unchanged, and builds `SITE_URL + path` for both `<link rel="canonical">` and `og:url`. Query strings are dropped, so the filtered home page and the cookie-filtered home page point at `/`. Month pages keep their trailing slash, because that's the address they're served at.

Pages that shouldn't be indexed get `noindex` and no canonical:
- search results;
- digest management pages;
- the 404 page.

When `improve-sitemap`'s area pages ship, a filtered home page with a single area could point at that area's page instead. That's left to that change.

### 3. JSON-LD is built from models in one module
`core/structured_data.py` has one function per type. Each returns a dict, and the template renders it with `json_script`-style escaping in `<script type="application/ld+json">`.

| Page | Type | What it carries |
|---|---|---|
| home | `WebSite` | `name` (`SITE_NAME`), `url` |
| band page | `MusicGroup` | `name`, `url`, `foundingLocation` (town and state from our record), `sameAs`, `event` (its next 10 upcoming approved events, each a `MusicEvent`) |
| artist page | `Person` | the same fields as a band, with `homeLocation` in place of `foundingLocation` |
| event page | `MusicEvent` | `name`, `startDate` (with the New York offset), `endDate` when known, `eventStatus` (`EventCancelled` when cancelled), `eventAttendanceMode` offline, `location` as a `MusicVenue` with the sheet's street address and town, `performer` (the event's performers in billing order, each `MusicGroup` or `Person` with its page `url`), `offers` (the ticket URL, price when known, `USD`), `url` |
| venue page | `MusicVenue` | `name`, `address` (the sheet's), `url`, `event` (its next 10 upcoming approved events) |

The tables follow these rules:
- `sameAs` uses only links an editor or MusicBrainz gave: the act's website, MusicBrainz, Wikidata, Wikipedia, Bandcamp page URL and Instagram;
- `image` appears only when the act has a freely licensed photo with its credit;
- a SeatGeek event's `offers.url` is the show's own Etix or AXS page, or the venue's ticket page, as the listing does, never SeatGeek.

Never included:
- Google Places data (address, coordinates, phone), under the Places terms;
- Last.fm data;
- Spotify or Apple Music IDs or names;
- Wikipedia text.

*Alternative:* microdata in the templates. Rejected: it spreads through the stored event HTML and is harder to test.

### 4. The sitemap becomes an index of sections
`nycnoise/urls.py` serves `sitemap.xml` as Django's sitemap index over these sections:

| Section | What it lists |
|---|---|
| `pages` | home, static pages, `/bands` |
| `months` | from the earliest month with an approved New England event, up to 12 months ahead |
| `acts` | live bands and artists, with `lastmod` from `updated_at` |
| `events` | upcoming approved New England events, with `lastmod` (past event pages are `noindex`, per `event-pages`, so they aren't listed) |
| `venues` | active New England venues, with `lastmod` |

All sections share a base that uses `SITE_URL`. Entries are sorted, so the files are stable, and each file stays under the 50,000-URL limit.

`updated_at` (`auto_now`) is added to `Band`, `Artist`, `Event` and `Venue`. The `queryset.update()` calls that change what a page shows set it themselves; the tasks list them.

Inactive acts stay in the sitemap: their pages stay open (`hide-inactive-acts-from-index`), and a past band's page can still answer a search.

### 5. Search Console by DNS, Bing by import
A domain property for `stagehopper.app` covers every subdomain and protocol. Its TXT record is added in Cloudflare (through the Cloudflare connector, with the owner's approval), so nothing goes into the page. Then the sitemap is submitted in Search Console. Bing Webmaster Tools imports the property and sitemap from Search Console. Both are free.

### 6. OpenSEO, hosted, within the plan's usage
Hosted OpenSEO costs $10 a month and includes $10 of usage (1,000 credits = $1). The owner creates the account, connects Search Console in the project's Google integrations (no Google Cloud project needed), and signs in the OpenSEO MCP server (`https://app.openseo.so/mcp`) in this workspace. The workspace's OpenSEO skills then drive the runs: `seo-project-setup` for the project's context, `seo-audit`, `keyword-research`, `local-seo`, `ai-visibility-audit` and `seo-report`.

| Run | What it does |
|---|---|
| baseline audit | a site audit crawl of `stagehopper.app` without Lighthouse or JavaScript rendering (no credits; the pages are server-rendered), within the plan's page limit |
| keyword research | for about 30 starter searches: "live music <state>", "concerts <city> this weekend", "<venue> shows" for the 20 busiest venues, and the site's name |
| rank tracking | 20 of those searches |
| AI visibility | a check of the same starter searches |

Each credit-spending run's estimated cost is shown to the owner first, and the month stays within the included $10 unless the owner raises it at G2. Search Console reads, reports and plain audits are free.

The findings are written to `docs/seo/<date>-baseline.md`:
- the top issues, with the URLs affected;
- the keywords' volumes and difficulty;
- the starting ranks.

Each fix is filed as an issue, or as a follow-up change when it's major. A re-audit and ranking check repeat monthly by hand, each saved as a dated report in `docs/seo/`.

*Alternatives:*
- **Self-hosting on Render.** OpenSEO's standalone Docker deploy is a Compose stack: a runtime container with a 2 GB memory limit and a persistent volume, plus an S3-compatible storage container (RustFS) with its own volume. Render doesn't run Compose, so it would be two services, each with a disk: a web service on the Standard plan for the memory, and a private service for storage. That's about $25–35 a month, against $10 hosted. It would also need its own DataForSEO account ($50 minimum top-up), our own Google OAuth client for Search Console, and its password sign-in kept up to date, since anyone who can reach it can spend the DataForSEO balance. It saves the hosted plan's 28% fee on DataForSEO requests, which matters only at far higher usage than ours.
- **Self-hosting on Cloudflare** (OpenSEO's one-command deploy, which runs on Cloudflare's free plan). We already have the Cloudflare account. It's the better self-hosted option, if usage ever grows enough for the 28% fee to outweigh running it ourselves; it still needs the DataForSEO account and OAuth client.

OpenSEO's crawler identifies itself, and the site has no rate limiting that would block it. A crawl of about 4,000 pages is well within what the web service handles.

### 7. The default description
`DEFAULT_DESCRIPTION` becomes "Live music calendar for New England: concerts, DJ nights and open mics at venues across Massachusetts, Connecticut, Rhode Island, New Hampshire, Maine and Vermont."

## Risks / Trade-offs

- [Structured data that disagrees with the page can draw a Search Console penalty] → It's built from the same records the page shows, and tests compare them. The Rich Results Test is run on one page of each kind before release.
- [The canonical address could hide filtered views that people search for] → Filtered views aren't indexed today either. `improve-sitemap`'s area pages are the planned indexable form.
- [OpenSEO's per-run costs for research aren't published] → Each credit-spending run is approved by the owner, within the plan's included $10. Automation waits until costs are known.
- [The sitemap's events section could grow large] → Only upcoming events are listed (about 5,000), and the index keeps each file under the limit.
- [`updated_at` is missed by some `queryset.update()`] → A test lists the update calls in the event and act code paths, and checks that each sets it.

## Testing

- **Django tests:**
  - `robots.txt` content and status, and that it isn't redirected;
  - the canonical URL and `og:url` on the home page (with filters and cookie), a month page, an act page, and the noindex pages;
  - the JSON-LD of each type against a fixture, including the never-included fields;
  - the sitemap index, its five sections (past events left out, inactive and out-of-area venues left out), sort order, `lastmod`, and the 12-month range;
  - `updated_at` moving on an edit.
- **Not automated:** the Search Console, Bing and OpenSEO setup. They're outside the site and recorded in the tasks with their results. The Cloudflare TXT record is checked with a DNS lookup.
