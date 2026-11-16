## 0. Before building

- [ ] 0.1 Confirm `add-event-pages` and `add-venue-pages` are built and archived, so the `event-pages` and `venue-pages` specs exist. Verify: both are in `openspec/specs/`.

## 1. Crawling and addresses

- [ ] 1.1 Serve `/robots.txt` from a view routed first in `nycnoise/urls.py` (design decision 1). Verify: "Fetching robots.txt" and "Not redirected".
- [ ] 1.2 Build the canonical link and `og:url` from the served path without query strings in `get_meta()` and `base.html`; mark search results, digest pages and the 404 page noindex. Verify: "A filtered home page", "An act page", "A month page" and "Search results", and that existing share-tag tests pass.
- [ ] 1.3 Change `DEFAULT_DESCRIPTION` (design decision 7). Verify: "The home page's description".

## 2. Structured data

- [ ] 2.1 Add `core/structured_data.py` with `WebSite`, `MusicGroup`, `Person`, `MusicEvent` and `MusicVenue` builders, following the source rules (design decision 3), and render them in `base.html`, the act page, the event page and the venue page. Verify: "A band with an upcoming show", "A cancelled show", "An artist", "An event page", "A venue page", "The home page", "Its canonical address and structured data", "A venue matched on Google Places", "An act matched on Spotify and Apple Music" and "A SeatGeek event".
- [ ] 2.2 Check one act page, one event page, one venue page and the home page with Google's Rich Results Test after deploy, and record the result here. Verify: no errors on any of them, and the event page qualifies for event rich results.

## 3. Sitemap

- [ ] 3.1 Add `updated_at` to `Band`, `Artist`, `Event` and `Venue` (migration), and set it in every `queryset.update()` that changes what their pages show. Verify: "An edited band", and a test that an import or enrichment update moves it.
- [ ] 3.2 Split the sitemap into an index of pages, months (to 12 months ahead), acts, events and venues sections, sorted, on `SITE_URL`. Verify: "The index", "Far-off months left out", "Events in range", "Venues listed", "A stable order", and the existing band-pages sitemap scenarios.

## 4. Measurement (with the owner)

- [ ] 4.1 With the owner's approval, add the Search Console TXT record for `stagehopper.app` in Cloudflare; the owner verifies the domain property and submits `/sitemap.xml`, and imports it into Bing Webmaster Tools. Verify: a DNS lookup shows the record, and Search Console reports the sitemap read with no errors.
- [ ] 4.2 The owner creates the hosted OpenSEO account ($10 a month), connects Search Console in the project's Google integrations, and signs in the OpenSEO MCP server here; set up the project's context with the `seo-project-setup` skill. Verify: a read-only OpenSEO call answers for `stagehopper.app`.
- [ ] 4.3 With each credit-spending run's cost estimate approved within the plan's included $10, run the baseline audit (without Lighthouse or JavaScript rendering), keyword research, rank tracking and AI visibility check (design decision 6), and write `docs/seo/<date>-baseline.md`. Verify: the report lists the top issues with URLs, keyword volumes and starting ranks, with the money spent.
- [ ] 4.4 File each audit finding as an issue, or as a follow-up change when it is major. Verify: every finding in the report links to its issue or change, or says why it was accepted as is.

## 5. Finish

- [ ] 5.1 Update `PRODUCTION.md` (robots, canonical rule, structured-data sources, the sitemap sections, Search Console and OpenSEO and the monthly check) and `AGENTS.md` (OpenSEO as a paid, approved-per-run service). Verify: they describe what shipped.
- [ ] 5.2 Run the whole suite with the network blocked and styles compiled. Verify: it passes.
