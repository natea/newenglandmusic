## 1. Before building

- [ ] 1.1 With Nate, on Render: confirm the workspace is on Pro or higher. On a throwaway pull request with previews on, check that a `sync: false` value of an environment group set in the dashboard reaches the preview. If it doesn't, stop and revise the design to the bucket fallback.
- [ ] 1.2 Write in `PRODUCTION.md` how to make the read-only role (`CREATE ROLE … LOGIN PASSWORD …; GRANT CONNECT …; GRANT USAGE ON SCHEMA public …; GRANT SELECT ON ALL TABLES IN SCHEMA public …; ALTER DEFAULT PRIVILEGES … GRANT SELECT …`). Nate makes it in the database's shell and fills the `preview-seed` group.

## 2. The scrub

- [ ] 2.1 Add `scrub_preview_data`:
  - it refuses unless `IS_PULL_REQUEST` is `true`;
  - it replaces users' emails and passwords and empties `Event.user_submission_email`;
  - it deletes the people-only tables' rows;
  - it creates or updates `preview-admin` from `PREVIEW_ADMIN_PASSWORD`.

  Verify with tests for "People-only tables", "Personal fields" and "Nate checks an admin change", and a test that it refuses without `IS_PULL_REQUEST`.
- [ ] 2.2 Keep the people-only tables in one list, used by the seed and the scrub. Add a test that fails when a model with an `EmailField` is neither in the list nor scrubbed.

## 3. The seed

- [ ] 3.1 Add `bin/preview-seed.sh`: dump through `PREVIEW_SOURCE_DATABASE_URL` without the listed tables' data, restore with `--clean --if-exists`, `migrate`, then `scrub_preview_data`. It fails with the step named, and refuses unless `IS_PULL_REQUEST` is `true`. Verify locally against a scratch copy, for "Seeded", "A pull request with a migration" and "The seed fails".

## 4. The blueprint

- [ ] 4.1 In `render.yaml`:
  - `previews: generation: automatic, expireAfterDays: 7`;
  - the web service's `initialDeployHook: ./bin/preview-seed.sh`, `buildFilter.ignoredPaths` (`openspec/**`, `docs/**`) and preview plans;
  - the database's `previewPlan`;
  - `previews: generation: off` on the three cron jobs;
  - the `preview-seed` environment group, linked by the web service only;
  - `previewValue: ""` for `DEFAULT_FROM_EMAIL`, the AWS, API, sheet-sync and analytics keys.

  Verify with a test that reads `render.yaml`, as the scheduled-jobs tests do, for "No jobs" and the preview values.
- [ ] 4.2 Describe previews in `PRODUCTION.md`: what they cost, how long they live, the read-only role, the admin password, and how to turn them off.

## 5. Live check

- [ ] 5.1 With Nate's G4 and go-ahead: merge, let the blueprint sync, and on the next code pull request check that:
  - a preview deploys and is seeded;
  - its listing matches the live site's;
  - it has no subscribers and no live admin email;
  - `preview-admin` signs in;
  - asking for the weekly email sends nothing;
  - a spec-only pull request gets no preview;
  - merging deletes the preview.
