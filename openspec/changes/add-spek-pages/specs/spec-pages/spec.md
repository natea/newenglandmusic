## Purpose

Publish the newenglandmusic project's OpenSpec specs and changes as Spek pages on the fork's GitHub Pages, so every proposal can be read in a browser, from the main branch and from each change's own branch, including while its owner reviews it.

## ADDED Requirements

### Requirement: Main's specs are published at the site root

A push to `main` that touches `openspec/` or the Spek workflow, `.github/workflows/spek.yml`, SHALL publish Spek's page for `main` as the `index.html` at the root of natea/newenglandmusic's GitHub Pages site, replacing only that file and `.nojekyll`.

#### Scenario: The main page

- **WHEN** `bin/publish-spek-page` publishes a page for the branch `main` into a site folder that already holds `changes/add-triage-clarify/index.html`
- **THEN** the folder's `index.html` is the new page, and `changes/add-triage-clarify/index.html` is unchanged

#### Scenario: Main's trigger

- **WHEN** the tests read the Spek workflow
- **THEN** it runs on pushes to `main` that touch `openspec/**` or `.github/workflows/spek.yml`

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
- **THEN** its publish step runs only when the build step succeeded, stops at its first failing command, starts `gh-pages` afresh only when `git ls-remote --exit-code` reports the branch missing, and pushes with `--force-with-lease` naming the commit it fetched

#### Scenario: No removal on delete

- **WHEN** the tests read the Spek workflow
- **THEN** it has no `delete` trigger and no step that removes a page

### Requirement: The build is pinned and least-privileged

The workflow SHALL use Spek's action and Spek's build at the same pinned commit, check out the full history, write only to the `gh-pages` branch, pass branch names to commands only through the environment, and ask for no permission beyond writing the repository's contents.

#### Scenario: Pinned and narrow

- **WHEN** the tests read the Spek workflow
- **THEN** it uses `spekhq/spek` and `spek-version` at commit `5542fa2dfda6c52a08fb0610a140670052056c66` (v1.20.2), checks out with `fetch-depth: 0`, asks only for `contents: write`, names no branch but `gh-pages` in a push, and puts no `${{ github.ref` or `${{ github.event` expression inside a `run:` script

#### Scenario: Never upstream

- **WHEN** the tests read the Spek workflow
- **THEN** it doesn't name nycnoise/nycnoise, and its job runs only when the repository is natea/newenglandmusic

### Requirement: Publishes queue, and never block the site's deploy

Publishes SHALL run one at a time without dropping any queued run, and a failed publish SHALL NOT fail the commit's checks, since Render deploys `main` only when every check on the commit passes. A deploy may still wait for the publish to finish.

#### Scenario: One at a time

- **WHEN** the tests read the Spek workflow
- **THEN** it has one concurrency group for every run, which doesn't cancel a run in progress and queues up to the maximum

#### Scenario: A failed publish doesn't fail the commit

- **WHEN** the tests read the Spek workflow
- **THEN** every step of its job may fail without failing the job

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
