## 1. Before building (with Nate)

- [ ] 1.1 On the vendors' current pages and the new accounts, check and record in `PRODUCTION.md`, with the date:
  - Cloud Run's prices and its free allowance in `us-east1`;
  - Neon's free plan: branches, compute hours, storage;
  - that a branch can be made from `base`, and that `pg_restore --clean --single-transaction` into `base` works while a child branch exists;
  - Artifact Registry's storage price.

  If a figure changes the proposal's cost or the 9-preview limit, tell Nate before going on.
- [ ] 1.2 Find which settings event pages and the discovery deck need to show players at request time, and which of them are secrets. Give Nate the list for open question 5.
- [ ] 1.3 Nate creates the Google Cloud project for previews, in `us-east1`, with billing and a budget alert, and turns on Cloud Run and Artifact Registry. Set up keyless sign-in for this repository, a deploy service account, and a runtime service account with no roles. Record the steps in `PRODUCTION.md`.
- [ ] 1.4 Write in `PRODUCTION.md` how to make the read-only role on Render's database: `CONNECT`, `USAGE` on the schema, `SELECT` on all tables and sequences, and default privileges for future ones. Nate makes it.
- [ ] 1.5 Nate creates the Neon account and project (Postgres 17, `aws-us-east-1`), and adds the secrets: `PREVIEW_SOURCE_DATABASE_URL` in the GitHub environment `preview-base` (deployment branch `main` only); `NEON_API_KEY` and `PREVIEW_ADMIN_PASSWORD` for the repository.

## 2. The data

- [ ] 2.1 Add `core/preview_data.py`: every table as copied, left out or cleaned. Verify with a test for "A new table".
- [ ] 2.2 Add `scrub_preview_data`, built from those lists, refusing under other settings or a database host that isn't local or Neon's. Verify with tests for "People-only tables" and "Personal fields", and for both refusals.
- [ ] 2.3 Add `set_preview_admin`. Verify with tests for "Signing in as the preview admin" and "A live account".

## 3. Preview settings and the image

- [ ] 3.1 Add `nycnoise/settings/preview.py` and the noindex middleware above WhiteNoise. Verify with tests for "Not indexed" (a page and a static file), "The data export", "Signing up for the weekly email" and "A stored play button".
- [ ] 3.2 Bring the `Dockerfile` in line with Render (Python 3.11.14, placeholders at build, gunicorn on `$PORT`) and add `.dockerignore`. Verify by running the image locally against a scratch database with the listed variables and loading the listing. `django.yml` is unchanged.

## 4. The decisions and scripts

- [ ] 4.1 Add `core/preview_plan.py`: which pull requests get a preview, the variable list, the deployment payload, and what the sweep removes. Verify with tests for "Changes to specs only", "A pull request from a fork", "Dependabot", "What a preview is given", "No jobs", "Closed without merging" and "Idle"; that a rebuild by hand refuses a fork's or Dependabot's pull request; and, for "Something saved on a preview", that the database a preview is given is its own branch's and never the source.
- [ ] 4.2 Add the `bin/preview-*` scripts over a small Neon and GitHub client and one `gcloud` function, with fakes for the tests. Verify with tests for "A build's pull request", "Reopened", "A tenth preview", "A pull request with a migration", "A new push", "A migration rewritten", "Merged" and "Rebuilt by hand", each checking the calls made.

## 5. The workflows

- [ ] 5.1 Add `.github/workflows/preview-base.yml`: the nightly copy on the runner (the role check, dump, migrate, scrub, load into `base`), then the sweep; runnable by hand. Verify with tests that read the file (schedule, the `preview-base` environment, the repository guard), and tests of the copy's script, against a local Postgres, for "The nightly copy", "The copy fails", "A role that can write" and "Cleaned before it is stored".
- [ ] 5.2 Add `.github/workflows/preview.yml`. Verify with tests that read the file: its triggers, the fork and Dependabot conditions, concurrency per pull request, permissions, the repository guard, and that it names no `preview-base` environment.
- [ ] 5.3 Describe previews in `PRODUCTION.md`: what they cost, how long they live, the accounts and secrets, the admin password, rebuilding by hand, and how to turn them off.

## 6. Live check

- [ ] 6.1 With Nate's G4 and go-ahead: merge, and run the nightly copy once by hand. Check "The nightly copy" on the real base: the listing's data is there, and the people-only tables are empty.
- [ ] 6.2 On the next code pull request, check on the real services:
  - "A build's pull request": the preview deploys, GitHub shows `preview-pr-<n>` as successful, and the bridge moves the issue to `preview-ready` with the address;
  - "Something saved on a preview": a venue saved there doesn't appear on the live site;
  - "Signing in as the preview admin";
  - "Not indexed" and "The data export";
  - "Changes to specs only": a spec-only pull request gets no preview;
  - "Merged": merging deletes the service and the branch, and the deployments show inactive.
