## 1. Accounts (with Nate)

- [ ] 1.1 Nate creates the Google Cloud project for previews, with billing and a budget alert, and turns on Cloud Run and Artifact Registry. Set up Workload Identity Federation for this repository and the deploy service account. Record the steps in `PRODUCTION.md`.
- [ ] 1.2 Nate creates the Neon project (Postgres 17, `aws-us-east-1`) and an API key.
- [ ] 1.3 Write in `PRODUCTION.md` how to make the read-only role on Render's database. Nate makes it and adds `PREVIEW_SOURCE_DATABASE_URL`, `NEON_API_KEY` and `PREVIEW_ADMIN_PASSWORD` as GitHub secrets.

## 2. The scrub

- [ ] 2.1 Add `scrub_preview_data`:
  - it refuses unless `DJANGO_SETTINGS_MODULE` is `nycnoise.settings.preview`;
  - it replaces users' emails and passwords, and empties `Event.user_submission_email`;
  - it deletes any rows in the people-only tables;
  - it sets `preview-admin` from `PREVIEW_ADMIN_PASSWORD`;
  - `--admin-only` does only the last step.

  Verify with tests for "People-only tables", "Personal fields" and "Nate checks an admin change", and a test that it refuses under other settings.
- [ ] 2.2 Keep the people-only tables in one list, used by the copy and the scrub. Add a test that fails when a model with an `EmailField` is neither listed nor scrubbed.

## 3. Preview settings and the image

- [ ] 3.1 Add `nycnoise/settings/preview.py` and the noindex middleware. Verify with tests for "Not indexed" and "Signing up for the weekly email", and a test that no API, analytics or mail setting is set.
- [ ] 3.2 Bring the `Dockerfile` in line with Render (Python 3.11.14, no build secret, gunicorn on `$PORT`), and add a CI job that builds it. Verify by running the image locally against a scratch database and loading the listing.

## 4. The workflows

- [ ] 4.1 Add `.github/workflows/preview-base.yml`: the nightly copy into `base-next`, the scrub and the swap; then the sweep. It can also be run by hand. Verify a run against a scratch Neon project for "The nightly copy" and "The copy fails".
- [ ] 4.2 Add `.github/workflows/preview.yml`:
  - on open, push and reopen: build, branch, migrate, set the admin, deploy, and record the deployment;
  - on close: delete and mark the deployment inactive;
  - `paths-ignore` for `openspec/**` and `docs/**`;
  - skip pull requests from forks and Dependabot.

  Verify on a throwaway pull request for "A build's pull request", "A pull request with a migration", "A new push" and "Merged".
- [ ] 4.3 Describe previews in `PRODUCTION.md`: what they cost, how long they live, the accounts and secrets, the admin password, and how to turn them off.

## 5. Live check

- [ ] 5.1 With Nate's G4 and go-ahead: merge, run the nightly copy once by hand, and on the next code pull request check that:
  - a preview deploys and GitHub shows its `preview-pr-<n>` deployment;
  - its listing matches the live site's;
  - it has no subscribers and no live admin email;
  - `preview-admin` signs in;
  - asking for the weekly email sends nothing;
  - a spec-only pull request gets no preview;
  - merging deletes the service and the branch.
