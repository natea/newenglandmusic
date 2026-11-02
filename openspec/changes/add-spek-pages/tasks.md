## 1. Placing a page

- [ ] 1.1 Add `bin/publish-spek-page <branch> <page> <site>`, in Python:
  - `main` → `<site>/index.html`;
  - `change/<name>` → `<site>/changes/<name>/index.html`, with `<name>` matching `[A-Za-z0-9_][A-Za-z0-9._-]*`;
  - anything else exits non-zero and writes nothing;
  - it always writes `<site>/.nojekyll`, and replaces only the one `index.html`.

  Add `core/tests/test_spek_pages.py` with tests for "The main page", "A change page" and "Branches that get no page".

## 2. The workflow

- [ ] 2.1 Add `.github/workflows/spek.yml`:
  - triggers: `push` to `change/*` only, with `paths: [openspec/**, .github/workflows/spek.yml]`; a daily `schedule` and `workflow_dispatch`, both building `main`; no `delete` trigger;
  - `permissions: contents: write`;
  - the `natea/newenglandmusic` guard on the job;
  - `concurrency: { group: spek-pages, cancel-in-progress: false, queue: max }`;
  - `continue-on-error: true` on every step;
  - checkout with `fetch-depth: 0`;
  - `spekhq/spek@5542fa2dfda6c52a08fb0610a140670052056c66`, with `id: build`, the same `spek-version`, a title, and an output path outside the checkout;
  - one publish step, `if: steps.build.outcome == 'success'`, a shell script with `set -euo pipefail`:
    - `git ls-remote --exit-code --heads origin gh-pages`, its exit code captured (`rc=0; … || rc=$?`) rather than tripping `set -e`: 2 starts an orphan `gh-pages`, 0 fetches it and notes its commit, anything else stops;
    - `bin/publish-spek-page "$BRANCH" …` with `BRANCH: ${{ github.ref_name }}` from `env:`;
    - amend the branch's single commit as `github-actions[bot]`, and push with `--force-with-lease=gh-pages:<that commit>`, or `--force-with-lease=gh-pages:` (the branch must still not exist) the first time.
- [ ] 2.2 Add tests, parsing the workflow with PyYAML (`data[True]` is `on:`), checking among other things that the build step has `id: build` and the gate names it, for "Main's trigger", "Change branches' trigger", "A failure can't wipe the pages", "No removal on delete", "Pinned and narrow", "Never upstream", "One at a time" and "A failed publish doesn't fail the commit".

## 3. The rule and the guide

- [ ] 3.1 In `AGENTS.md`:
  - define G2 as the owner confirming a proposal, and G4 as the owner accepting its implementation;
  - in the OpenSpec section: a proposal's draft is committed, with "Draft" in its subject, and its `change/` branch pushed to natea/newenglandmusic before G2, so it has a Spek page at `https://natea.github.io/newenglandmusic/changes/<name>/`; the confirmation is recorded by an empty commit "Confirm proposal <name> (G2)"; keep host and network names out of OpenSpec files;
  - in the line on pushing (now "Render deploys its `main` branch, so push only when asked"): `change/` branches may be pushed to natea/newenglandmusic without asking; `main` and the upstream still need the owner.

  `CLAUDE.md` links to `AGENTS.md`, so one edit covers both. Add a test for "The rule is written down".
- [ ] 3.2 Add `docs/SPEK.md`:
  - the site's address and a change page's address;
  - which pushes publish, and that a branch needs `.github/workflows/spek.yml`, from `main`, to get a page;
  - that each page shows the whole repository's OpenSpec, with the change found by name;
  - that pages stay after a branch is deleted;
  - to keep host and network names out of OpenSpec files.

  Add a test for "Guide addresses". Run the full suite (`python manage.py test`).

## 4. Live check

One go-ahead from Nate covers 4.2. Pushing `change/` branches is his standing go-ahead.

- [ ] 4.1 Push `change/add-spek-pages` to natea/newenglandmusic. Check the workflow run succeeds, which also shows GitHub accepts the file and its `queue: max`, and creates `gh-pages` holding `changes/add-spek-pages/index.html` and `.nojekyll`. Check the commit's Django and Render checks are unaffected.
- [ ] 4.2 With Nate's go-ahead, turn GitHub Pages on for the fork from `gh-pages` at `/`. Open `https://natea.github.io/newenglandmusic/changes/add-spek-pages/` and check the change shows with its proposal, design, tasks and spec. Record the run and what was seen here.

## Workflow follow-up

These come after Nate's G4, the archive and the merge, so they aren't tasks:
- With Nate's go-ahead, push `main`, which also deploys the site on Render as today. Check that no Spek run started for that push. Start the workflow by hand, and check that the root page appears and `changes/add-spek-pages/` is still served.
- Merge `main` into `change/add-triage-clarify`, push it, and give Nate its page's address.
