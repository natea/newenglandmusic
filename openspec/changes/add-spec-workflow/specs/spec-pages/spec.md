## ADDED Requirements

### Requirement: A change's sketches are published beside its page

When `bin/publish-spek-page` publishes a `change/<name>` branch, it SHALL also copy every `openspec/changes/<name>/sketches/*.html` file in the checkout to `changes/<name>/sketches/` in the site folder. Each publish SHALL replace that change's `sketches/` folder whole, and SHALL touch no other change's files or the root page. Main's publish copies no sketches.

#### Scenario: Sketches published

- **WHEN** `change/add-venue-hours` is published and its checkout has `openspec/changes/add-venue-hours/sketches/a.html`, `b.html` and `c.html`
- **THEN** the site folder has `changes/add-venue-hours/sketches/a.html`, `b.html` and `c.html` beside `changes/add-venue-hours/index.html`, and the other changes' files are unchanged

#### Scenario: A sketch removed

- **WHEN** the site has `changes/add-venue-hours/sketches/c.html` and the branch no longer has `c.html`
- **THEN** after the publish the site has no `changes/add-venue-hours/sketches/c.html`

#### Scenario: No sketches on main

- **WHEN** `main` is published
- **THEN** no `sketches/` folder is written anywhere
