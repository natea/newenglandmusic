# Tasks

## 1. Guide and rules

- [ ] 1.1 Write `docs/SEO.md` with the sections "Connecting", "The project", "Running an audit", "Costs" and "Findings", covering: the official plugin and browser sign-in, no key in the repository or chat, the by-hand route for an agent without plugins, one project for the production address only, the brief as the source of the project's context, free and paid steps, asking before spending, and findings shown to the owner before any issue is opened. Verify: the guide tests in 1.4 pass.
- [ ] 1.2 Add OpenSEO to the "Paid and rate-limited APIs" list in `AGENTS.md` (ask before spending credits; previews are never audited), and a line pointing to `docs/SEO.md`. Verify: the `AGENTS.md` tests in 1.4 pass.
- [ ] 1.3 Link the guide from `docs/ONBOARDING.md`. Verify: the link opens the guide on GitHub.
- [ ] 1.4 Add `core/tests/test_seo_audits.py` with tests for the scenarios "Guide sections", "Agents are pointed to the guide", "The guide states the rule", "The guide names the production address", "The guide separates free from paid", "OpenSEO is in the paid-services list" and "The guide describes the hand-off". Verify: `manage.py test core.tests.test_seo_audits` passes.
- [ ] 1.5 Add the test for "No OpenSEO setting is declared", reading `.env.example`, `render.yaml`, `.github/workflows/django.yml` and `.fabro/workflows/build/workflow.fabro`. Verify: it passes, and fails when a line `OPENSEO_API_KEY=''` is added to `.env.example` by hand and then removed.

## 2. Search brief

- [ ] 2.1 Write `docs/seo/project-context.md` with the sections "What the site is", "Who it is for", "Page families" and "Competing sites", from the site as it is today (the listing, month archives, band and artist pages, and the pages `improve-sitemap` plans, marked as planned). Verify: the tests in 2.3 pass.
- [ ] 2.2 Nate reviews the brief, in particular "Who it is for" and "Competing sites". Verify: his changes are committed, or he says none are needed.
- [ ] 2.3 Add tests for "Brief sections" and "The guide names the brief as the source". Verify: `manage.py test core.tests.test_seo_audits` passes.

## 3. Audit summaries

- [ ] 3.1 Add tests for "Summaries are named and shaped alike", "No account detail in a summary" and "Issue links in a summary point at the site's repository", written to pass over every file in `docs/seo/audits/`, with small sample texts in the test for the failing cases (a bad date, a missing section, an email address, an issue link to another repository). Verify: `manage.py test core.tests.test_seo_audits` passes.
- [ ] 3.2 Add the test for "A baseline exists". Verify: it fails until task 4.5 adds the first summary, then passes.

## 4. Connection and baseline audit

- [ ] 4.1 Nate signs in to OpenSEO from the coding agent, in the browser, and confirms the account has a plan or credits. Verify: the agent's connection check and project listing both succeed.
- [ ] 4.2 Create the OpenSEO project for the production address if the listing shows none, and copy its context from `docs/seo/project-context.md`. Verify: the project listing shows exactly one project for the site, and its context matches the file.
- [ ] 4.3 Create the `seo` label on the site's repository. Verify: `gh label list` shows it.
- [ ] 4.4 Read the account's balance, tell Nate what the baseline audit is expected to spend, and wait for his go-ahead. Verify: his go-ahead is in the conversation before any paid step runs.
- [ ] 4.5 Run the baseline audit of the production site with the SEO audit skill (performance pass off), and write `docs/seo/audits/<date>.md` with "Verdict", "Recommendations", "Issues" and "Not checked". Verify: the tests in group 3 pass, including "A baseline exists".
- [ ] 4.6 Show Nate the recommendations; open an issue labelled `seo` for each one he accepts, citing the summary and the evidence; mark the others declined in the summary; and fill in the summary's "Issues" section. Verify: every accepted recommendation has an issue link in the summary, and the group 3 tests still pass.
- [ ] 4.7 Write any durable fact the audit learned into `docs/seo/project-context.md`, then update the OpenSEO project from it. Verify: the file and the project's context match.

## 5. Whole-change check

- [ ] 5.1 Run the full suite with outbound network blocked. Verify: it passes, with no test reaching OpenSEO.
