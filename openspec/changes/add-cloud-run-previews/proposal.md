## Why

Sooz, Mark and Nate need to see a change working before it merges. Today it can be judged only by its diff, or by merging it, which puts it on the live site. Nate asked for previews on a copy of the live data, not demo data (9 November 2026), and chose a preview step before the merge (`building → preview-ready → awaiting-merge`, 12 November).

`add-preview-environments` proposed Render's preview environments. They cost about $30–40 a month: Render's $25 Pro plan, plus a web service and a database billed for each preview. On 17 November Nate asked for a proposal with **Cloud Run and Neon** as the foundation. A Cloud Run service scales to zero, and Google's free monthly allowance covers review traffic. A Neon branch is an instant copy of a database, free for up to 10 branches. So the same previews cost about $0–3 a month. The two proposals are alternatives for the same capability: Nate picks one at G2, and the other is closed unbuilt.

## What Changes

- **A cleaned copy of the live data waits in Neon.** Each night a GitHub Actions job copies the live database through a read-only role into a Neon project's base branch, leaving out the tables that hold only people's data. It then replaces the remaining personal fields: admin emails and passwords, and the submitter's email on events.
- **Each pull request gets its own preview.** For each pull request against `main` from a branch of this repository that changes code, a GitHub Actions workflow:
  1. builds the site's container image;
  2. branches the Neon base as `pr-<number>` and applies the pull request's migrations to the branch;
  3. deploys a Cloud Run service, `preview-pr-<number>`, at its own `run.app` address;
  4. reports the address to GitHub as a deployment of the environment `preview-pr-<number>`.

  This starts as soon as the pull request opens, so the change is reviewed on its preview before it merges; merging is the approval (Nate, 18 November 2026). Intentable's bridge moves the issue to `preview-ready` on that deployment's success and posts the address, linking the pages the build named (`add-preview-paths`).

  This starts as soon as the pull request opens, so the change is reviewed on its preview before it merges; merging is the approval (Nate, 18 November 2026). Intentable's bridge moves the issue to `preview-ready` on that deployment's success and posts the address, linking the pages the build named (`add-preview-paths`).

  A push redeploys the service on the same branch, so data saved on the preview stays.
- **A preview ends with its pull request.** When the pull request is merged or closed, the workflow deletes the service and the Neon branch, and marks the deployment inactive. A daily sweep deletes any preview whose pull request has had no push for 7 days, and any preview left behind.
- **A preview never reaches the outside world.** It has no mail sender and no keys for outside APIs, analytics or the sheet sync. It has no scheduled jobs. It asks search engines not to index it. The play buttons stored in event pages still show.
- **A preview admin can sign in,** as `preview-admin`, with a password kept for previews only.
- **The container image matches production.** The fork's `Dockerfile` came from upstream nycnoise and has drifted: Python 3.12 instead of 3.11.14, and a `.env` secret at build time. It is brought in line with Render's build and start commands, so a preview runs the same code the same way.

Out of scope:
- **The issue side, in intentable:** posting the preview's address, moving the issue to `preview-ready` and asking "looks right?". The bridge will read the `preview-pr-<n>` deployments, as `add-delivery-board` reads production's.
- **Previews of pull requests from forks of the repository, and Dependabot's.** GitHub withholds secrets from them, and they shouldn't run with this repository's cloud credentials anyway.
- **Keeping a preview after its pull request closes unmerged.** The pull request stays open to keep it; the board shows it in `awaiting-merge`.

## Open questions for G2

1. **A Google Cloud project and billing account.** The change needs a new project with billing on Nate's account (or Jazkarta's?) and a budget alert. Which account pays?
2. **A Neon account.** The free plan allows 10 branches in a project: the base plus 9 open previews. Is that enough, or should the workflow refuse a tenth preview with a note on the pull request?
3. **How long an idle preview lives:** 7 days without a push is proposed.
4. **Who can open a preview.** Anyone with the address, so Sooz and Mark need no Google sign-in. The data holds nothing personal, and the address isn't published beyond the issue. A password gate is the alternative.
5. **Where the copy runs.** A GitHub Actions runner connects to Render's database from outside. Render allows outside connections today. If Nate later limits them to listed addresses, the nightly copy moves to a Render cron job that writes to Neon.

## Capabilities

### New Capabilities

- `preview-environments`: a preview of the site for each pull request, on its own copy of a cleaned nightly snapshot of the live data, cut off from email, outside APIs, analytics and scheduled jobs, and removed with its pull request.

### Modified Capabilities

None. Production's build, jobs and data are unchanged; the `Dockerfile` isn't used by Render.

## Impact

- **Code:**
  - `.github/workflows/preview.yml` (deploy and remove a pull request's preview);
  - `.github/workflows/preview-base.yml` (the nightly copy, and the daily sweep);
  - `Dockerfile` (Python 3.11.14, no build-time secret, gunicorn as Render starts it);
  - a management command, `scrub_preview_data`;
  - `nycnoise/settings/preview.py`;
  - `PRODUCTION.md`.
- **Accounts:**
  - a Google Cloud project with Cloud Run and Artifact Registry, and keyless sign-in from GitHub Actions (Workload Identity Federation);
  - a Neon project;
  - GitHub secrets for the read-only database role, Neon's API key and the preview admin's password.
- **Render:** one read-only Postgres role on the live database. Nothing else changes.
- **Cost:** about $0–3 a month: image storage, plus compute above Cloud Run's free allowance. A budget alert on the Google Cloud project catches surprises.
- **Alternative to:** `add-preview-environments` (Render). Only one of the two is built.
