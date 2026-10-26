# Tasks

## 1. Upgrade and the https link default

- [x] 1.1 Pin `Django==5.2.17` in `requirements.txt`. Verify: `makemigrations --check` reports no changes and `showmigrations` shows nothing unapplied against the local database (done in `dec5139`).
- [x] 1.2 Set `assume_scheme="https"` on the submission form's link fields and through `formfield_overrides` on `EventAdmin` and `VenueAdmin` (done in `dec5139`).
- [x] 1.3 Tests for the "Event submitted with scheme-less links" and "Venue website entered in the admin without a scheme" scenarios (`test_links_without_a_scheme_get_https` and `test_website_without_a_scheme_gets_https`, done in `dec5139`).
- [x] 1.4 Tests for the "Explicit http is kept" scenario, on the submission form and in the venue admin. Verify: the new tests pass.
- [x] 1.5 Merge `main` into `django5` and run the full suite on 5.2, network-blocked, with `-W error::django.utils.deprecation.RemovedInDjango60Warning`. Verify: every test passes.
- [x] 1.6 Make the submission form's link and ticket link fields plain text boxes with the url keyboard (`inputmode="url"`), still validated as links on the server. Verify: typing `nateaune.com` at localhost:8002/submit-event submits and saves `https://nateaune.com`.
- [x] 1.7 Tests for the "Link fields are plain text boxes" and "Something that isn't a link is rejected" scenarios. Verify: the new tests pass and the full suite passes on 5.2.

## 2. Checks the tests can't make

- [ ] 2.1 In the 5.2 admin at localhost:8002, logged in, check each interactive widget: TinyMCE on an event and a static page, the venue autocomplete on an event, the date and time pickers, sortable menu items, and the event and venue list filters. Verify: each works, and the browser console shows no errors. Note any broken widget and upgrade only that package.
- [x] 2.2 Update the comment on the Django rule in `.github/dependabot.yml`: major versions stay skipped, so Django 6 arrives as its own change. Verify: the file still parses as YAML.

## 3. Release

- [ ] 3.1 With the user's go-ahead, push `django5` to `github` and open a pull request to `main`. Verify: CI passes on the pull request.
- [ ] 3.2 Merge and watch the Render deploy. Verify: the build log shows "No migrations to apply" and the home page, an event link and the admin load on the live site.
- [ ] 3.3 Rebuild the local `venv/` from `requirements.txt` and remove the `../nycnoise-django5` checkout and its `venv-django5/`. Verify: `venv/bin/python -c "import django; print(django.__version__)"` prints 5.2.x and the suite passes.

## Workflow follow-up

- Archive with `/opsx:archive` once every task is checked.
