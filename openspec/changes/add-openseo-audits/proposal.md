# Proposal

## Why

Nobody has measured how StageHopper does in search. The site has a sitemap and a meta description, and `improve-sitemap` is adding venue, event and area pages, but which of those pages people actually search for, and what stops them ranking, is guesswork. OpenSEO gives a coding agent real search data (crawl results, rankings, keyword demand, competitors) and guided audit workflows, so the next SEO work can be chosen on evidence.

OpenSEO's plugin is already installed in the owner's coding agent but has never been signed in to, has no project for the site, and nothing in this repository says how to use it, what it costs, or where its findings go.

## What Changes

This change adopts hosted OpenSEO as the project's SEO audit tool. It adds a documented way of working, not a site feature: no models, views, templates or scheduled jobs change.

- **A guide, `docs/SEO.md`:** how an agent connects to OpenSEO (the official plugin, signing in through the browser), how to run an audit, what costs credits, and what happens to the findings.
- **The site's search brief, `docs/seo/project-context.md`:** what StageHopper is, who it is for, its page families, and the sites it competes with. This file is the source of truth; the OpenSEO project's context is copied from it.
- **One OpenSEO project, for the production address only.** Previews and local servers are never audited.
- **Dated audit summaries in `docs/seo/audits/`:** each audit leaves a short summary in the repository with its verdict, its recommendations, and the issue opened for each one the owner accepts.
- **Findings become GitHub issues.** A recommendation the owner accepts is opened as an issue with the `seo` label, and then goes through the same triage, proposal and build steps as any other issue. An audit never changes the site directly.
- **No credential in the repository.** Sign-in is the owner's, through the browser. No OpenSEO key goes in `.env`, `.env.example`, `render.yaml` or a test fixture.
- **Spending needs a go-ahead.** `AGENTS.md` lists OpenSEO among the paid services: free reads need no permission, and anything that spends credits states its expected cost and waits for the owner.
- **A baseline audit** of the production site, run once the owner has signed in, as the first dated summary.

**Out of scope:**
- Fixing anything an audit finds. Each fix is its own issue and, where it is a major change, its own proposal.
- Audits on a schedule, rank tracking, and AI-answer tracking. These spend credits continuously; they can be proposed once a baseline shows what is worth tracking.
- Giving OpenSEO to the unattended agents that triage and build issues. Only an agent working with the owner uses it.
- Self-hosting OpenSEO.
- Connecting Google Search Console or Analytics. The audit works without them; the guide says how the owner can connect them later.

## Capabilities

### New Capabilities

- `seo-audits`: how the project audits the site's search visibility with OpenSEO: the guide, the search brief, which address is audited, where summaries are kept, how findings become issues, and the rules on credentials and spending.

### Modified Capabilities

None. `site-identity` and `site-analytics` are unchanged, and the sitemap behaviour belongs to `improve-sitemap`.

## Impact

- **New files:** `docs/SEO.md`, `docs/seo/project-context.md`, `docs/seo/audits/<date>.md` (one per audit), and a configuration test, `core/tests/test_seo_audits.py`, that reads them.
- **Changed files:** `AGENTS.md` (the paid-services list, and a pointer to the guide) and `docs/ONBOARDING.md` (a link to the guide).
- **Code, models, migrations, templates, `render.yaml`:** none.
- **External service:** hosted OpenSEO, reached only from a coding agent through its plugin. The site and its jobs never call it, and the tests never do.
- **GitHub:** a new `seo` label, and issues opened from accepted findings. A new issue starts the triage workflow, as any issue does.
- **Cost:** an OpenSEO account for the owner. The plugin is free; hosted OpenSEO is paid by plan and credits. What the baseline audit costs is read from the account before it runs.
- **`improve-sitemap`:** not blocked by this change and not changed by it. The baseline audit may reorder which of its parts is built first.
