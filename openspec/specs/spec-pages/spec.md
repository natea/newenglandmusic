# spec-pages Specification

## Purpose
Publish the newenglandmusic project's OpenSpec specs and changes as Spek pages on the fork's GitHub Pages, so every proposal can be read in a browser, from the main branch and from each change's own branch, including while its owner reviews it.

## Requirements

### Requirement: Main's specs are published at the site root

The Spek workflow, `.github/workflows/spek.yml`, SHALL publish Spek's page for `main` as the `index.html` at the root of natea/newenglandmusic's GitHub Pages site once a day and when started by hand, replacing only that file and `.nojekyll`. It SHALL NOT run on a push to `main`, so no Spek check sits on `main`'s commits and Render's deploy never waits for one (Nate's decision, 2 November 2026).

#### Scenario: The main page

- **WHEN** `bin/publish-spek-page` publishes a page for the branch `main` into a site folder that already holds `changes/add-triage-clarify/index.html`
- **THEN** the folder's `index.html` is the new page, and `changes/add-triage-clarify/index.html` is unchanged

#### Scenario: Main's trigger

- **WHEN** the tests read the Spek workflow
- **THEN** it runs on a daily schedule and on demand, and no push trigger names `main`

### Requirement: Each change branch gets its own page

A push to a branch named `change/<name>` that touches `openspec/` or the Spek workflow SHALL publish Spek's page for that branch as `changes/<name>/index.html` on the same site. `<name>` SHALL be letters, digits, `.`, `_` and `-` only, not starting with `.` or `-`.

#### Scenario: A change page

- **WHEN** `bin/publish-spek-page` publishes a page for the branch `change/add-triage-clarify`
- **THEN** the site folder gets `changes/add-triage-clarify/index.html`, and nothing else changes but `.nojekyll`

#### Scenario: Branches that get no page

- **WHEN** `bin/publish-spek-page` is given the branch `fabro-setup`, `change/a/b`, `change/.hidden` or `change/$(id)`
- **THEN** it exits with a failure and writes nothing into the site folder

#### Scenario: Change branches' trigger

- **WHEN** the tests read the Spek workflow
- **THEN** it runs on pushes to branches matching `change/*` that touch `openspec/**` or `.github/workflows/spek.yml`

### Requirement: Pages are kept

A change's page SHALL stay published when its branch is deleted, so links to it keep working; it shows the branch's last published state. A failed step SHALL NOT remove any page: the publish SHALL run only after Spek's build succeeded, SHALL start the `gh-pages` branch afresh only when it doesn't exist, and SHALL push only over the `gh-pages` commit it fetched.

#### Scenario: A failure can't wipe the pages

- **WHEN** the tests read the Spek workflow
- **THEN** its publish step runs only when the build step succeeded, stops at its first failing command, starts `gh-pages` afresh only when `git ls-remote --exit-code` reports the branch missing, and pushes with `--force-with-lease` naming the commit it fetched, or requiring the branch still be absent when it started one

#### Scenario: No removal on delete

- **WHEN** the tests read the Spek workflow
- **THEN** it has no `delete` trigger and no step that removes a page

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

### Requirement: Draft proposals are published before the owner confirms them

A proposal SHALL be committed as a draft and its `change/<name>` branch pushed to natea/newenglandmusic before the owner confirms the proposal (the gate called G2 in the change cycle), so the owner can read it on its Spek page while reviewing it. `AGENTS.md` SHALL say so, define G2, say how the confirmation is recorded, give the standing go-ahead for pushing `change/` branches, and say to keep host and network names out of OpenSpec files.

#### Scenario: The rule is written down

- **WHEN** the tests read `AGENTS.md`
- **THEN** it defines G2 as the owner confirming a proposal, says a proposal's draft is pushed on its `change/` branch before G2 with "Draft" in its commit, says the confirmation is recorded by a commit "Confirm proposal <name> (G2)", names the change page's address, allows pushing `change/` branches without asking while `main` and the upstream still need the owner, and says to keep host and network names out of OpenSpec files

### Requirement: A guide says where the pages are

`docs/SPEK.md` SHALL give the site's address, a change page's address, which pushes publish, that a branch gets a page only once it contains the Spek workflow, that each page shows the whole repository's OpenSpec with the change found by name, that pages stay after a branch is deleted, and to keep host and network names out of OpenSpec files.

#### Scenario: Guide addresses

- **WHEN** the tests read `docs/SPEK.md`
- **THEN** it names `https://natea.github.io/newenglandmusic/` and `https://natea.github.io/newenglandmusic/changes/<name>/`, says a branch needs `.github/workflows/spek.yml` to get a page, that a page shows the whole repository's OpenSpec, and that pages stay, and asks to keep host and network names out

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
