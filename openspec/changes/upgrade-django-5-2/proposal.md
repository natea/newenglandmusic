# Proposal

## Why

The site runs on Django 4.2, whose security support ended in April 2026. The Django advisories still open on 4.2 are fixed only in 5.2, which is the current long-term support release (supported until April 2028). We held off in case the upgrade was large. A trial on the `django5` branch shows it is small: no migrations, no other package changes, and the whole test suite passes.

## What Changes

- Pin Django 5.2 (5.2.17 at the time of writing) instead of 4.2.30. No other package has to change. Newer versions of some add-on packages are available, and the design says which to take now.
- **BREAKING (small):** a web address typed without a scheme, such as `example.com`, is saved as `https://example.com` instead of `http://example.com`. This covers the event submission form and the event and venue admin forms. Django 6 makes `https` the default, and opting in now clears the only Django 6 deprecation warning in our code.
- Keep the Dependabot rule that skips major Django versions, so Django 6 also arrives as its own change. Update its comment to say so.
- Deploy to Render through the normal `main` branch, after CI passes on the upgrade.

## Capabilities

### New Capabilities

- `link-entry`: how web addresses that people type into the site's forms and the admin are completed and stored.

### Modified Capabilities

None. The other specs' behavior is unchanged. The upgrade is checked against them by the existing test suite, rather than by new requirements.

## Impact

- **Dependencies:** `requirements.txt` (Django only).
- **Code:** `core/views/event_submission.py` (the two link fields) and `core/admin.py` (`EventAdmin` and `VenueAdmin` link fields).
- **Tests:** new tests for the https default. The full suite must pass on 5.2 with Django 6 deprecation warnings treated as errors.
- **Database:** no migrations. 4.2 and 5.2 can share one database, so a rollback is a code revert only.
- **Hosting:** Render builds from `main` and runs `migrate` in `bin/build.sh`; it has nothing to apply. Postgres is 17 on Render and in CI and 16 locally, all within Django 5.2's minimum of 14.
- **Tooling:** `.github/dependabot.yml` comment. Developers make a fresh virtualenv from `requirements.txt`.
