## 1. Before building (with Nate)

- [x] 1.1 On the vendors' current pages and the new accounts, check and record in `PRODUCTION.md`, with the date:
  - Cloud Run's prices and its free allowance in `us-east1`;
  - Neon's free plan: branches, compute hours, storage;
  - that a branch can be made from `base`, and that `pg_restore --clean --single-transaction` into `base` works while a child branch exists;
  - Artifact Registry's storage price.

  If a figure changes the proposal's cost or the 9-preview limit, tell Nate before going on.
- [x] 1.2 Find which settings event pages and the discovery deck need to show players at request time, and which of them are secrets. Add them to what a preview is given, and tell Nate which are secrets.
  - Done 18 November 2026: the two switches plus placeholders for the five credentials; none is a real secret (see the design).
- [x] 1.3 Nate creates the Google Cloud project for previews in his own account, in `us-east1`, with billing and a budget alert, and turns on Cloud Run and Artifact Registry. Set up keyless sign-in for this repository, a deploy service account, and a runtime service account with no roles. Record the steps in `PRODUCTION.md`.
  - Done 18 November 2026, except the budget alert and the `PRODUCTION.md` notes: project `stagehopper-previews`, registry `previews` in `us-east1`, service accounts `preview-deployer` and `preview-runtime`, and the sign-in pool `github` with provider `newenglandmusic`.
- [x] 1.4 Write in `PRODUCTION.md` how to make the read-only role on Render's database: `CONNECT`, `USAGE` on the schema, `SELECT` on all tables and sequences, and default privileges for future ones. Nate makes it.
- [x] 1.5 Nate creates the Neon account and project (Postgres 17, `aws-us-east-1`), and adds the secrets: `PREVIEW_SOURCE_DATABASE_URL` in the GitHub environment `preview-base` (deployment branch `main` only); `NEON_API_KEY`, `PREVIEW_ADMIN_PASSWORD_HASH` (made with Django's `make_password` on his own machine) for the repository.
  - Done 18 November 2026. The role `preview_reader` exists on the production database (task 1.4's SQL, run by Nate; its notes for `PRODUCTION.md` are still to write), and all three secrets are set.

## 2. The data

- [x] 2.1 Add `core/preview_data.py`: every table as copied, left out or cleaned. Verify with a test for "A new table".
- [x] 2.2 Add `scrub_preview_data`, built from those lists, refusing under other settings or a database host that isn't local or Neon's. Verify with tests for "People-only tables" and "Personal fields", and for both refusals.
- [x] 2.3 Add `set_preview_admin`. Verify with tests for "Signing in as the preview admin" and "A live account".

## 3. Preview settings and the image

- [x] 3.1 Add `nycnoise/settings/preview.py` and the noindex middleware above WhiteNoise. Verify with tests for "Not indexed" (a page and a static file), "The data export", "Signing up for the weekly email", "Players on a preview" and "A stored play button".
- [x] 3.2 Bring the `Dockerfile` in line with Render (Python 3.11.14, placeholders at build, gunicorn on `$PORT`) and add `.dockerignore`. Verify by running the image locally against a scratch database with the listed variables and loading the listing. `django.yml` is unchanged.
  - Done 18 November 2026 on the Spark (arm64): the image builds, migrates a scratch Postgres 17, and serves the listing, the admin login and a static file with the noindex header; `/internal-api/db` answers 404 and another host is refused. `libsass` has no arm64 wheel, so the image installs a compiler for that step.

## 4. The decisions and scripts

- [x] 4.1 Add `core/preview_plan.py`: which pull requests get a preview, the variable list, the deployment payload, and what the sweep removes. Verify with tests for "Changes to specs only", "A pull request from a fork", "Dependabot", "What a preview is given", "No jobs", "Closed without merging" and "Idle"; that a rebuild by hand refuses a fork's or Dependabot's pull request; and, for "Something saved on a preview", that the database a preview is given is its own branch's and never the source.
- [x] 4.2 Add the `bin/preview-*` scripts over a small Neon and GitHub client and one `gcloud` function, with fakes for the tests. Verify with tests for "A build's pull request", "Reopened", "Every slot in use", "A slot held by a closed pull request", "A pull request with a migration", "A new push", "A migration rewritten", "Merged" and "Rebuilt by hand", each checking the calls made.

## 5. The workflows

- [x] 5.1 Add `.github/workflows/preview-base.yml`: the nightly copy on the runner (the role check, dump, migrate, scrub, load into `base`), then the sweep; runnable by hand. Verify with tests that read the file (schedule, the `preview-base` environment, the repository guard), and tests of the copy's script, with stand-ins for the Postgres tools, for "The nightly copy", "The copy fails", "A role that can write" and "Cleaned before it is stored".
- [x] 5.2 Add `.github/workflows/preview.yml`. Verify with tests that read the file: its triggers, the fork and Dependabot conditions, concurrency per pull request, permissions, the repository guard, and that it names no `preview-base` environment.
- [x] 5.3 Describe previews in `PRODUCTION.md`: what they cost, how long they live, the accounts and secrets, the admin password, rebuilding by hand, and how to turn them off.

## 6. Live check

- [x] 6.1 With Nate's G4 and go-ahead: merge, and run the nightly copy once by hand. Check "The nightly copy" on the real base: the listing's data is there, and the people-only tables are empty.
  - Done 19 November 2026 (UTC), run 44445419057, after fix 7.1. Read over a direct connection, `base` held 5,396 events, 729 venues, 2,813 acts and 3,664 Spotify links; no subscribers, sign-in codes, weekly-email choices, mail requests, sessions, admin log entries or accounts; no submitter email; and no job run with output or an error.
- [ ] 6.2 On the next code pull request, check on the real services:
  - [x] "A build's pull request": the preview deploys, GitHub shows `preview-pr-<n>` as successful, and the bridge moves the issue to `preview-ready` with the address.
    - Done 19 November 2026: rebuilt by hand for #147 (issue 36) after fixes 7.2 and 7.3; issue 36 moved to `preview-ready` with its preview's address. "Rebuilt by hand" held too.
  - [ ] "Something saved on a preview": a venue saved there doesn't appear on the live site;
  - [ ] "Signing in as the preview admin" (Nate, with his password);
  - [x] "Not indexed" and "The data export": checked on #154's and #156's previews, every response carried the header and `/internal-api/db` answered 404;
  - [ ] "Changes to specs only": a spec-only pull request gets no preview;
  - [x] "Merged": merging #154, #155, #156 and #157 deleted each one's service and branch.
  - [ ] An ordinary pull request opened by a build gets its preview with no hand step.

## 7. Fixes from the first real runs

- [x] 7.1 The copy refused the read-only role: Postgres writes a boolean joined to text as `false`, and the check compared it with `f`. The query now answers `reads` or `writes`, and anything but `reads` refuses (#155).
- [x] 7.2 Previews and the copy connect to Neon directly, never through its pooler, which hands one session's settings to the next: the restore left an empty `search_path` that hid every table (#156).
- [x] 7.3 A preview is built from the pull request merged into today's `main`, and the workflow makes that merge itself: a branch from before previews existed has no image or `bin/preview`, and GitHub's `refs/pull/<n>/merge` can be days stale (#156, #157). Verified by the workflow test for "A branch from before a change to main" and "A pull request that conflicts with main", and live on #147.
