# Design

## Context

See `proposal.md` for the motivation. What shapes the approach:

- **OpenSEO is an agent tool, not a library.** It is a hosted service reached through a coding agent's plugin: a connection to OpenSEO's server plus twelve guided skills (SEO audit, project setup, keyword research, competitor analysis, reports and others). Nothing in the Django project calls it.
- **The plugin is installed but unused.** In the owner's coding agent the plugin and its skills are present, but it has never been signed in to, so only its sign-in step is offered. There is no OpenSEO project for the site.
- **An OpenSEO project carries its own context.** The audit skill reads a project's business overview and key pages, and writes back what it learns. That context lives in the owner's OpenSEO account, where nobody reviewing the repository can see it.
- **Some steps spend credits.** The plugin is free; hosted OpenSEO charges by plan and credits. Checking the connection, listing or creating projects, and reading a finished crawl are free. Rankings, keyword demand and live result checks are not.
- **Previews are deliberately unindexed.** A preview's settings add a header asking search engines to leave it alone. Production sends no such header and serves a sitemap.
- **The project already tests its documents.** Existing configuration tests read guides and workflow files and check their sections (`docs/FABRO.md`, `render.yaml`). This change uses the same pattern.
- **A new issue starts work.** Issues on the site's repository are triaged automatically, so opening one is not free of consequence.

## Goals / Non-Goals

**Goals:**
- Any agent working with the owner can run an audit by following one guide, and gets the same project, the same brief and the same rules.
- What an audit found, and what was done about it, can be read in the repository without an OpenSEO login.
- No way for a credential to reach the repository, and no way to spend credits without the owner knowing the expected cost.

**Non-Goals:**
- Wrapping OpenSEO in a management command or calling it from the site. The audit is a judgement-heavy conversation, and the skills already drive it.
- Storing OpenSEO's full reports or raw data in the repository. The summary links ideas to issues; the full report stays in OpenSEO.
- Deciding in advance what the site should fix. That is the audit's job.

## Decisions

**1. Use the hosted service through the official plugin.**
The plugin bundles the connection and the skills and updates them together. Alternatives: adding the server by hand and copying skills (more to maintain, and the guide says the plugin is preferred), or self-hosting (a second service to run for one site's occasional audits). The guide covers the by-hand route in one paragraph, for an agent that can't take plugins.

**2. Keep the search brief in the repository and copy it to OpenSEO.**
`docs/seo/project-context.md` is reviewed like any other file and survives a change of OpenSEO account. The direction is one-way: file to project. When an audit learns something durable (a corrected description, a page worth naming), the agent edits the file in the same piece of work and then updates the project from it. Alternative: let the OpenSEO project be the only copy, which is what the skills do by default, but then the brief is invisible to reviewers and to an agent that isn't signed in.

**3. One project, for the production address.**
The address is the host of the default `SITE_URL`. Previews would crawl as "not indexable" and the host's own address redirects to the production one, so both would waste a crawl and mislead. The guide says to check for an existing project before creating one, so a second agent doesn't make a duplicate.

**4. A short dated summary per audit, not the report.**
OpenSEO's report is saved in OpenSEO. The repository gets `docs/seo/audits/<date>.md` with four fixed sections, so audits can be compared over time and each accepted finding traced to its issue. The summary never holds account details; the test checks for email addresses, credit balances and key-shaped strings.

**5. The owner accepts findings before any issue exists.**
The agent shows the recommendations and opens an issue only for those the owner accepts, each labelled `seo` and citing its summary. Opening issues for everything would start a triage run per finding, including ones the owner would have declined. Declined findings stay in the summary so the next audit doesn't raise them as new.

**6. Spending follows the project's existing rule.**
`AGENTS.md` already says to ask before a run that spends money. OpenSEO gets an entry in that list. In practice the agent reads the balance, says what the audit is expected to use, and waits. Crawl depth is left at the skill's default and the performance (Lighthouse) pass stays off unless the owner asks, which also keeps the crawl light on the site.

**7. Tests read files; nothing is mocked because nothing is called.**
The spec's scenarios are all about files in the repository, so `core/tests/test_seo_audits.py` reads them, in the style of the existing configuration tests. OpenSEO is never imported or requested by project code, so there is no client to mock and the suite still passes with outbound network blocked. The sign-in, the project and the baseline audit are done by the owner and an agent, and are verified by the summary file they leave.

**8. Unattended agents don't get OpenSEO.**
The agents that triage and build issues run without the owner present, so they could neither sign in nor ask before spending. They work from the issue text, which carries the audit's evidence.

## Risks / Trade-offs

- **The brief and the OpenSEO project drift apart** → the guide makes the file the source and tells an agent to compare them at the start of an audit.
- **An audit's estimates are read as measurements** → provider traffic and keyword counts are estimates. The summary's "Recommendations" cite the evidence, and "Not checked" says when first-party data (Search Console) was missing.
- **A document test is only as strong as its wording checks** → the tests check sections, named files and forbidden content, not prose quality. The owner reviews the guide and brief at acceptance.
- **Credit costs change** → the guide gives no prices. It tells the agent to read the balance and state the expected spend each time.
- **Pages are still thin.** Until `improve-sitemap` adds venue, event and area pages, a baseline will mostly say that the site has few pages to rank. That is still useful: it tells us which of those parts to build first, and gives a "before" to compare against.
- **Audit summaries are public.** The repository and its pages are public, so a summary is visible to competitors. It holds no account detail, and nothing in it is secret.

## Migration Plan

Nothing is deployed. The guide, brief and tests merge first; the owner then signs in, the project is created, and the baseline audit runs. To back out, remove the files and the `AGENTS.md` entry; the OpenSEO project can be deleted from the owner's account.

## Open Questions

- **Search Console.** Connecting it would add real clicks and impressions, and needs the owner to verify the domain with Google. It is left for after the baseline, since the audit treats its absence as a gap, not a blocker.
- **How often to audit.** Decided after the baseline, once it is clear how fast the site's search picture changes.
