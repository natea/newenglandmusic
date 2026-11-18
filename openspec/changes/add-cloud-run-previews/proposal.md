## Why

Sooz, Mark and Nate need to see a change working before it merges. Today it can be judged only by its diff, or by merging it, which puts it on the live site. Nate's decisions so far:
- **9 November 2026:** previews run on a copy of the live data, not demo data.
- **18 November 2026:** "the preview environment should be generated when a PR is submitted, so that the feature can be reviewed *before* being merged. once it has merged, it can be assumed that it's been reviewed". An issue goes `building` → `awaiting-merge` → `preview-ready` → `merged` → `deployed`, and merging is the approval.

Intentable's bridge already does its half (`add-delivery-board`, deployed 18 November). When a pull request's preview reports a successful GitHub deployment of the environment `preview-pr-<number>`, the bridge moves the issue to `preview-ready` and posts the preview's address.

`add-preview-environments` proposed Render's preview environments for the preview itself. On 17 November Nate asked for a proposal with **Cloud Run and Neon** as the foundation, expecting it to be much cheaper. The two proposals are alternatives for the same capability: Nate picks one at G2, and the other is closed unbuilt.

**Cost, not yet verified.** These figures come from the vendors' pricing pages as read on 17 November 2026, and task 1.1 checks them before anything is built:
- Render: about $30–40 a month. That is the $25 Pro plan, plus a web service and a database billed for each preview.
- Cloud Run and Neon: about $0–3 a month. A Cloud Run service scales to zero, and Google's free monthly allowance should cover review traffic. Neon's free plan allows 10 branches in a project, with limits on compute hours and storage that all previews share.
- Worst case: a preview kept busy all month, by a crawler for instance, could cost tens of dollars. A budget alert only emails; it doesn't stop anything.

## What Changes

- **A cleaned copy of the live data waits in Neon.** Each night a GitHub Actions job:
  1. copies the live database through a read-only role into a throwaway Postgres on the job's own runner;
  2. removes people's data there;
  3. loads the cleaned result into the Neon project's `base` branch.

  So data that hasn't been cleaned never reaches Neon. What is removed:
  - subscribers, sign-in codes, weekly-email choices and mail requests;
  - sessions, the admin's change log, and every admin account;
  - the submitter's email on events;
  - the output and errors stored with job runs.

  Every table is listed as copied, cleaned or left out, and a test fails when a new table isn't listed.
- **Each pull request gets its own preview, as soon as it opens.** For each pull request against `main` from a branch of this repository that changes code, a GitHub Actions workflow:
  1. builds the site's container image;
  2. branches the Neon base as `pr-<number>` and applies the pull request's migrations to the branch;
  3. deploys a Cloud Run service, `preview-pr-<number>`;
  4. reports its address to GitHub as a successful deployment of the environment `preview-pr-<number>`, which the bridge reads.

  A push redeploys the service on the same branch, so data saved on the preview stays. Pull requests from forks, Dependabot's, and ones that change only `openspec/` or `docs/` get no preview: those last have no code to look at, and each preview uses one of Neon's branches.
- **A preview ends when its pull request is merged, or after 7 idle days.** On merge, the workflow deletes the service and the Neon branch and marks the deployments inactive. A pull request closed *without* merging keeps its preview (open question 1). A daily sweep removes previews with no push for 7 days and anything left behind, and marks their deployments inactive. A swept preview can be rebuilt by hand from the Actions tab.
- **A preview never reaches the outside world.** It has no mail sender, no scheduled jobs, and no keys for outside APIs, analytics or the sheet sync, apart from any player settings Nate allows (open question 5). The inherited data-export endpoint (`/internal-api/db`) is switched off on previews. Every response asks search engines not to index it.
- **A preview admin can sign in,** as `preview-admin`, the only account on a preview, with a password kept for previews.
- **The container image matches production.** The fork's `Dockerfile` came from upstream nycnoise and has drifted: Python 3.12 where production uses 3.11.14, and a `.env` secret at build time. It is brought in line with Render's build and start commands. It is built only by the preview workflow, on pull requests. Nothing is added to the checks that production's deploys wait on.

**What a preview can't show.** The listing's play buttons are stored in each event's saved page, so they show as on the live site. Pages that build their players at request time, such as event pages and the discovery deck, need the Spotify, Apple Music and YouTube settings. Without them those pages show no players (open question 5).

Out of scope:
- **The issue side.** Intentable's bridge has it: `preview-ready`, the comment with the address, and the links to the pages to check, which the build names (`add-preview-paths`).
- **Previews of pull requests from forks of the repository, and Dependabot's.** GitHub withholds secrets from them.

## Open questions for G2

1. **A pull request closed without merging.** On 12 November Nate said: "we may close a PR but not yet merge it back to main … it may still be sitting on a preview branch and preview URL, but not yet deployed to prod." Proposed, to honour that: closing without merging **keeps** the preview until it has been idle 7 days. Idle counts from the last push, not from the close, so a pull request closed more than 7 days after its last push loses its preview that night. The alternative is to delete it on any close, as Render does, and keep the pull request open to keep the preview.
2. **A Google Cloud project and billing account,** with a budget alert. Which account pays: Nate's or Jazkarta's? An organisation's policy may forbid public Cloud Run services, which previews need.
3. **A Neon account** used for nothing else, since the pull request workflow holds its API key. The free plan's 10 branches mean the base plus 9 open previews. Proposed: a tenth pull request gets a failed check saying so.
4. **How long an idle preview lives:** 7 days without a push is proposed. A finished build waiting on Nate's merge gets no pushes, so its preview dies after 7 days and the issue's link goes dead until someone rebuilds it. Longer, such as 14 days, costs little.
5. **Players on previews.** Should previews get the Spotify, Apple Music and YouTube settings, so changes to players can be reviewed? Several recent issues were about exactly those (#63, #74). The cost is that those keys become readable by pull request code. Proposed: yes for the switches that need no key, and task 1.2 finds out which keys request-time rendering needs, for Nate to decide.
6. **Who can open a preview, and who has the admin password.** Proposed: anyone with the address can open a preview, so Sooz and Mark need no Google sign-in. The data holds nothing personal, and the address appears only on the issue. The `preview-admin` password is Nate's, shared with Sooz and Mark if he chooses. A password gate on the whole preview is the alternative.
7. **Nightly copy.** The plan left the refresh open (nightly, or once per preview). Nightly is proposed, so cleaning happens once, away from any preview.
8. **Unapproved submissions.** The copy keeps events that visitors submitted and nobody approved yet, with the submitter's own description, though not their email. They show only in a preview's admin. Proposed: leave them out of the copy. The alternative is to keep them, so the approval screens can be previewed with real examples.
9. **The read-only role on the live database** is the one change to production. Nate makes it himself (task 1.4); G2 is the yes for it.

## Capabilities

### New Capabilities

- `preview-environments`: a preview of the site for each pull request, on its own copy of a cleaned nightly snapshot of the live data, cut off from email, outside APIs, analytics and scheduled jobs.

### Modified Capabilities

None. Production's build, checks, jobs and data are unchanged, apart from the read-only role of open question 9; Render doesn't use the `Dockerfile`.

## Impact

- **Code:**
  - `.github/workflows/preview.yml` (deploy, rebuild and remove a pull request's preview);
  - `.github/workflows/preview-base.yml` (the nightly copy and the daily sweep);
  - `bin/preview-*` scripts and `core/preview_plan.py`, which hold the workflows' decisions so they can be tested;
  - `Dockerfile` and a new `.dockerignore`;
  - `core/preview_data.py`, and two management commands, `scrub_preview_data` and `set_preview_admin`;
  - `nycnoise/settings/preview.py`;
  - `PRODUCTION.md`.
- **Accounts:**
  - a Google Cloud project with Cloud Run and Artifact Registry, and keyless sign-in from GitHub Actions;
  - a Neon project in an account of its own;
  - GitHub secrets: the read-only database role, in an environment only `main`'s nightly job can use; and Neon's API key and the preview admin's password, for the pull request workflow.
- **Render:** one read-only Postgres role on the live database. Nothing else changes.
- **Alternative to:** `add-preview-environments` (Render). Only one of the two is built.
- **Works with:** `add-preview-paths`, which has the build name the pages to check.
