# Design

## Context

The trial upgrade is on the `django5` branch (commit `dec5139`), checked out at `../nycnoise-django5` with its own `venv-django5/`. That way the 4.2 dev server on port 8001 keeps running from `main`, and the 5.2 server runs on port 8002. Both share the local database, which was backed up first (`~/.local/share/nycnoise-backups/nycnoise-2026-10-26-0623-before-django5.dump`).

Already checked on 5.2.17:
- **Tests:** the full suite passes, including with Django 6 deprecation warnings raised as errors.
- **Migrations:** `makemigrations --check` finds nothing, and `showmigrations` shows nothing unapplied.
- **Pages:** 29 public and admin pages return the same status codes as on 4.2.
  - The public pages are identical, apart from the sitemap's order and the generated `.ics` ID and time.
  - The admin lists show the same rows on both versions.
  - All 45 admin scripts and stylesheets load.

Not yet checked: the admin's interactive widgets (TinyMCE, the venue autocomplete, date and time pickers, sortable menu items). Those need a browser and a logged-in admin.

## Goals / Non-Goals

**Goals:**
- Run on a supported Django release with as few changes as possible.
- Keep production data and behavior unchanged, apart from the https default for links.

**Non-Goals:**
- Django 6.x. It's a later, separate change; the Dependabot rule keeps it out until then.
- Upgrading add-on packages beyond what 5.2 requires.
- Fixing the deploy-time `check --deploy` warnings, which come from local development settings and are the same on 4.2.

## Decisions

**Target 5.2 LTS, not 6.1.** 5.2 has security support until April 2028, while 6.1 isn't a long-term support release and would need another upgrade sooner. 6.1 would also need newer major versions of add-on packages (for example django-debug-toolbar 8 and django-autocomplete-light 5). 5.2 needs none.

**Keep the other package pins as they are.** Every package works on 5.2 at its current version, as shown by the tests and page checks. A few don't list 5.2 in their metadata (django-autocomplete-light 3.12.1, django-ordered-model, django-js-asset), so the manual admin check in the tasks covers their widgets. Upgrading them would add risk without fixing anything, so it is left for the Django 6 change. If the manual check finds a broken widget, upgrading that one package is the fix.

**Set `assume_scheme="https"` on each link field instead of using the transitional setting.** Django 5.x offers `FORMS_URLFIELD_ASSUME_HTTPS = True`, but that setting raises its own deprecation warning and is removed in 6.0. Setting it per field (two form fields, plus `formfield_overrides` on `EventAdmin` and `VenueAdmin`) is silent and matches what Django 6 does by default. When we move to 6, those arguments can simply be removed.

**Deploy through `main` as usual.** Render deploys `main` after CI passes (`autoDeployTrigger: checksPass`), and its build runs `migrate`, which has nothing to apply. Opening a pull request from `django5` runs CI on Postgres 17 before anything deploys.

**Testing and external services.** This change adds no calls to external services. The new tests use only Django's form and admin classes and the test database. The existing mocks for gog, venue websites, Anthropic, Ticketmaster and Google Places are unchanged, and the suite runs with outbound network blocked, as now.

## Risks / Trade-offs

- [An admin widget's JavaScript breaks under the 5.2 admin, which the tests can't see.] → Manual check of each widget at localhost:8002 before merging. If one breaks, upgrade that one package.
- [Someone relies on a scheme-less link becoming `http://`.] → Very unlikely: venue and ticket sites are https. An explicit `http://` is still kept unchanged.
- [The deploy fails on Render.] → Revert the merge commit on `main`. With no migrations, the database works with either version.
- [Local virtualenvs drift.] → `venv/` is rebuilt from `requirements.txt` after the merge. The task list says so.

## Migration Plan

1. Merge `main` into `django5`, so the branch includes the latest fixes, and rerun the suite.
2. Do the manual admin check.
3. Push `django5` to `github` and open a pull request to `main`. CI runs the suite on Postgres 17.
4. Merge. Render builds, runs `migrate` (with nothing to apply) and deploys. Check the site and the admin there.
5. Rebuild the local `venv/` on 5.2, then remove the `../nycnoise-django5` checkout and its virtualenv.

**Rollback:** revert the merge on `main` and let Render redeploy. No database restore is needed. The pre-upgrade dump is there in case it is.
