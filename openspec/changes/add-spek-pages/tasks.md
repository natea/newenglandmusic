## 1. Placing a page

- [ ] 1.1 Add `bin/publish-spek-page <branch> <page> <site>`, in Python:
  - `main` → `<site>/index.html`;
  - `change/<name>` → `<site>/changes/<name>/index.html`, with `<name>` matching `[A-Za-z0-9_][A-Za-z0-9._-]*`;
  - anything else exits non-zero and writes nothing;
  - it always writes `<site>/.nojekyll`, and replaces only the one `index.html`.

  Add `core/tests/test_spek_pages.py` with tests for "The main page", "A change page" and "Branches that get no page".

## 2. The workflow

- [ ] 2.1 Add `.github/workflows/spek.yml`:
  - triggers: `push` to `main` and `change/*`, with `paths: [openspec/**, .github/workflows/spek.yml]`, and no `delete` trigger;
  - `permissions: contents: write`;
  - the `natea/newenglandmusic` guard on the job;
  - `concurrency: { group: spek-pages, cancel-in-progress: false, queue: max }`;
  - `continue-on-error: true` on every step;
  - checkout with `fetch-depth: 0`;
  - `spekhq/spek@5542fa2dfda6c52a08fb0610a140670052056c66` with the same `spek-version`, a title, and an output path outside the checkout;
  - a step that checks out `gh-pages` into a separate folder, or starts it as an orphan the first time, runs `bin/publish-spek-page "$BRANCH" …` with `BRANCH: ${{ github.ref_name }}` from `env:`, amends the branch's single commit as `github-actions[bot]`, and force-pushes `gh-pages`.
- [ ] 2.2 Add tests, parsing the workflow with PyYAML (`data[True]` is `on:`), for "Main's trigger", "Change branches' trigger", "No removal on delete", "Pinned and narrow", "Never upstream", "One at a time" and "A failed publish doesn't fail the commit".

## 3. The rule and the guide

- [ ] 3.1 In `AGENTS.md`'s OpenSpec section, add that a proposal's draft is committed and its `change/` branch pushed to natea/newenglandmusic before the owner's G2, so it has a Spek page at `https://natea.github.io/newenglandmusic/changes/<name>/`, and that the G2 commit records the confirmation. Add a test for "The rule is written down".
- [ ] 3.2 Add `docs/SPEK.md`:
  - the site's address and a change page's address;
  - which pushes publish, and that a branch needs `.github/workflows/spek.yml`, from `main`, to get a page;
  - that each page shows the whole repository's OpenSpec, with the change found by name;
  - that pages stay after a branch is deleted;
  - to keep host and network names out of OpenSpec files.

  Add a test for "Guide addresses". Run the full suite (`python manage.py test`).

## 4. Live check

One go-ahead from Nate covers 4.2. Pushing `change/` branches is his standing go-ahead.

- [ ] 4.1 Push `change/add-spek-pages` to natea/newenglandmusic. Check the workflow run succeeds and creates `gh-pages` holding `changes/add-spek-pages/index.html` and `.nojekyll`, and that the commit's Django and Render checks are unaffected.
- [ ] 4.2 With Nate's go-ahead, turn GitHub Pages on for the fork from `gh-pages` at `/`. Open `https://natea.github.io/newenglandmusic/changes/add-spek-pages/` and check the change shows with its proposal, design, tasks and spec. Record the run and what was seen here.

## 5. After the merge

These follow Nate's G4, archive and merge.

- [ ] 5.1 With Nate's go-ahead, push `main`, which also deploys the site on Render. Check that the root page appears, that `changes/add-spek-pages/` is still served, and that Render's deploy wasn't held up.
- [ ] 5.2 Merge `main` into `change/add-triage-clarify`, push it, and give Nate its page's address.
