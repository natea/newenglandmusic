# Spec Delta

## Purpose

How the project audits StageHopper's search visibility with OpenSEO: where the instructions and the site's search brief live, which address is audited, where audit summaries are kept, how findings become issues, and the rules that keep credentials out of the repository and spending under the owner's control.

## ADDED Requirements

### Requirement: A guide explains SEO audits

`docs/SEO.md` SHALL explain how an agent working with the owner connects to OpenSEO and audits the site. It SHALL have these sections: "Connecting", "The project", "Running an audit", "Costs" and "Findings". `AGENTS.md` SHALL point to it.

#### Scenario: Guide sections

- **WHEN** the configuration tests read `docs/SEO.md`
- **THEN** it has a heading for each of "Connecting", "The project", "Running an audit", "Costs" and "Findings"

#### Scenario: Agents are pointed to the guide

- **WHEN** the configuration tests read `AGENTS.md`
- **THEN** it names `docs/SEO.md`

### Requirement: Sign-in stays out of the repository

The connection to OpenSEO SHALL be the owner's own sign-in, made through the browser from the coding agent. The repository SHALL hold no OpenSEO key or token: not in `.env.example`, `render.yaml`, the GitHub Actions workflow, the build workflow's test environment, or a test fixture. The guide SHALL say so, and SHALL say that a key is entered only in the agent's own secret settings when browser sign-in can't be used.

#### Scenario: No OpenSEO setting is declared

- **WHEN** the configuration tests read `.env.example`, `render.yaml`, `.github/workflows/django.yml` and `.fabro/workflows/build/workflow.fabro`
- **THEN** none of them names a variable containing `OPENSEO`

#### Scenario: The guide states the rule

- **WHEN** the configuration tests read the guide's "Connecting" section
- **THEN** it says sign-in happens in the browser and that no key is written to the repository or to chat

### Requirement: The site's search brief is kept in the repository

`docs/seo/project-context.md` SHALL describe the site for an audit, with these sections: "What the site is", "Who it is for", "Page families" and "Competing sites". It SHALL be the source of truth for the OpenSEO project's context: when the two differ, the OpenSEO project is corrected from the file, and a durable fact an audit learns is written to the file in the same piece of work.

#### Scenario: Brief sections

- **WHEN** the configuration tests read `docs/seo/project-context.md`
- **THEN** it has a heading for each of "What the site is", "Who it is for", "Page families" and "Competing sites", and each section has text under it

#### Scenario: The guide names the brief as the source

- **WHEN** the configuration tests read the guide's "The project" section
- **THEN** it names `docs/seo/project-context.md` and says the OpenSEO project's context is copied from it

### Requirement: Only the production site is audited

There SHALL be one OpenSEO project for the site, for the production address that `SITE_URL` defaults to. Previews, local servers and the host's own address SHALL NOT be audited: previews ask search engines not to index them, so their results would mislead.

#### Scenario: The guide names the production address

- **WHEN** the configuration tests read the guide's "The project" section
- **THEN** it names the host of the default `SITE_URL` as the only address to audit, and says previews and local servers are not audited

### Requirement: Spending credits needs the owner's go-ahead

Checking the connection, listing projects, creating a project and reading results already paid for SHALL need no permission. Before any step that spends OpenSEO credits, the agent SHALL read the account's balance, tell the owner what it expects the step to cost, and wait for the owner's go-ahead. A go-ahead covers the audit it was given for, not later ones. `AGENTS.md` SHALL list OpenSEO among its paid services with this rule.

#### Scenario: The guide separates free from paid

- **WHEN** the configuration tests read the guide's "Costs" section
- **THEN** it says which steps are free, and that a step that spends credits states its expected cost and waits for the owner

#### Scenario: OpenSEO is in the paid-services list

- **WHEN** the configuration tests read the "Paid and rate-limited APIs" section of `AGENTS.md`
- **THEN** it has an entry for OpenSEO that says to ask before spending credits

### Requirement: Each audit leaves a dated summary

Each audit SHALL leave a summary at `docs/seo/audits/<YYYY-MM-DD>.md`, named for the day it ran, with these sections: "Verdict", "Recommendations", "Issues" and "Not checked".

- **"Recommendations":** each recommendation, with the evidence for it.
- **"Issues":** the issue opened for each accepted recommendation, or "none accepted".
- **"Not checked":** what the audit left out, such as Search Console data when it isn't connected.

#### Scenario: Summaries are named and shaped alike

- **WHEN** the configuration tests read every file in `docs/seo/audits/`
- **THEN** each is named `<YYYY-MM-DD>.md` with a real date, and has a heading for each of "Verdict", "Recommendations", "Issues" and "Not checked"

#### Scenario: A baseline exists

- **WHEN** the configuration tests list `docs/seo/audits/`
- **THEN** it holds at least one summary

### Requirement: A summary holds no account detail

An audit summary SHALL NOT contain the OpenSEO account's credit balance, the account's email address, or any key or token.

#### Scenario: No account detail in a summary

- **WHEN** the configuration tests read every file in `docs/seo/audits/`
- **THEN** none contains an email address, the word "credits" followed by a number, or a string shaped like an API key

### Requirement: Accepted findings become issues

An audit SHALL NOT change the site. The agent SHALL present the audit's recommendations to the owner, and for each one the owner accepts SHALL open an issue on the site's repository with the `seo` label, naming the summary it came from and the evidence. The issue then follows the project's usual steps. A recommendation the owner declines SHALL stay in the summary, marked as declined, and get no issue.

#### Scenario: The guide describes the hand-off

- **WHEN** the configuration tests read the guide's "Findings" section
- **THEN** it says recommendations are shown to the owner first, that each accepted one becomes an issue labelled `seo`, and that an audit changes no code

#### Scenario: Issue links in a summary point at the site's repository

- **WHEN** the configuration tests read the "Issues" section of each summary
- **THEN** every issue link in it is to an issue in `natea/newenglandmusic`
