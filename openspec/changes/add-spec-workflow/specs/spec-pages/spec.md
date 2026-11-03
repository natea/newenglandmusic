## MODIFIED Requirements

### Requirement: The build is pinned and least-privileged

The workflow SHALL use Spek's action and Spek's build at the same pinned commit, write only to the `gh-pages` branch, and pass branch names to commands only through the environment. Its `publish` job SHALL check out the full history and ask for no permission beyond writing the repository's contents; any other job SHALL ask only to read them.

#### Scenario: Pinned and narrow

- **WHEN** the tests read the Spek workflow
- **THEN** it uses `spekhq/spek` and `spek-version` at commit `5542fa2dfda6c52a08fb0610a140670052056c66` (v1.20.2), has no permissions at the top level, `publish` checks out with `fetch-depth: 0` and asks only for `contents: write`, `thumbnails` asks only for `contents: read`, names no branch but `gh-pages` in a push, and puts no `${{ github.ref` or `${{ github.event` expression inside a `run:` script

#### Scenario: Never upstream

- **WHEN** the tests read the Spek workflow
- **THEN** it doesn't name nycnoise/nycnoise, and its jobs run only when the repository is natea/newenglandmusic

### Requirement: Publishes queue, and never fail a commit's checks

Publishes SHALL run one at a time without dropping any queued run, and a failed publish SHALL NOT fail the checks of the commit it ran for.

#### Scenario: One at a time

- **WHEN** the tests read the Spek workflow
- **THEN** it has one concurrency group for every run, which doesn't cancel a run in progress and queues up to the maximum

#### Scenario: A failed publish doesn't fail the commit

- **WHEN** the tests read the Spek workflow
- **THEN** every step of its jobs may fail without failing the job

## ADDED Requirements

### Requirement: A change's sketches are published beside its page

When `bin/publish-spek-page` publishes a `change/<name>` branch, it SHALL also copy that change's sketches, if any: each regular UTF-8 file directly in `openspec/changes/<name>/sketches/` whose name ends in `.html` and that has no `http-equiv`, to `changes/<name>/sketches/` in the site folder. Each publish SHALL replace that change's `sketches/` folder whole, and SHALL touch no other change's files or the root page. Main's publish copies no sketches.

#### Scenario: A link instead of a file

- **WHEN** `sketches/a.html` is a symbolic link
- **THEN** it isn't published, and the other sketches are

#### Scenario: Sketches published

- **WHEN** `change/add-venue-hours` is published and its checkout has `openspec/changes/add-venue-hours/sketches/a.html`, `b.html` and `c.html`
- **THEN** the site folder has `changes/add-venue-hours/sketches/a.html`, `b.html` and `c.html` beside `changes/add-venue-hours/index.html`, and the other changes' files are unchanged

#### Scenario: A sketch removed

- **WHEN** the site has `changes/add-venue-hours/sketches/c.html` and the branch no longer has `c.html`
- **THEN** after the publish the site has no `changes/add-venue-hours/sketches/c.html`

#### Scenario: No sketches on main

- **WHEN** `main` is published
- **THEN** no `sketches/` folder is written anywhere

### Requirement: Published sketches get thumbnails

A separate job SHALL render each publishable sketch, with its policy, to a half-size screenshot `<sketch>.png` (Nate's request, 2 November 2026), and `bin/publish-spek-page` SHALL publish them beside the sketches. A thumbnail that can't be made SHALL be reported and SHALL NOT stop the publish.

#### Scenario: Thumbnails made

- **WHEN** `sketches/a.html`, `b.html` and `c.html` are rendered with a Chrome on `PATH`, and then published
- **THEN** the site folder has `a.png`, `b.png` and `c.png` beside them

#### Scenario: A thumbnail that can't be made

- **WHEN** no Chrome is on `PATH`, or it fails
- **THEN** the sketches are still published, with no thumbnail, and the scripts exit 0

### Requirement: Sketches are rendered apart from the write token

Chrome SHALL render sketches only in a job with read-only permission and no saved credentials, with its network cut. The job that pushes to `gh-pages` SHALL NOT run Chrome, because a sketch is written by an agent from issue text.

#### Scenario: Thumbnails rendered apart

- **WHEN** the tests read the workflow
- **THEN** the `thumbnails` job has `contents: read` and `persist-credentials: false`, the `publish` job needs it and runs no render, and Chrome's arguments cut name resolution

### Requirement: Published sketches can't run code or call out

Every sketch `bin/publish-spek-page` publishes SHALL begin, right after any doctype, with `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; form-action 'none'; base-uri 'none'">`, added by the script, so the browser refuses scripts, outside resources and form posts on the fork's Pages domain, even for a sketch pushed without the run's checker. A sketch with `http-equiv` SHALL be neither rendered nor published.

#### Scenario: A sketch that isn't UTF-8

- **WHEN** a sketch pushed by hand isn't UTF-8 text
- **THEN** it isn't rendered or published, and the other sketches are

#### Scenario: A sketch with http-equiv

- **WHEN** a sketch has `http-equiv`, which a policy tag can't stop
- **THEN** it isn't rendered or published, and the other sketches are

#### Scenario: Policy added

- **WHEN** `sketches/a.html` is published
- **THEN** the published copy starts with that policy after its doctype, and the rest of the file is unchanged

#### Scenario: A sketch with no head

- **WHEN** a sketch on a change branch has no `<head>` and starts with a `<script>`
- **THEN** the published copy starts with the policy, before the script
