## Why

Nate asked that whenever OpenSpec is used, the change's artifacts be published with Spek (2 November 2026), so a proposal can be read in a browser, by Nate at his gates, by Igor, and later by Sooz and Mark, instead of only in a terminal or on Nate's Mac. docs/plan.md in natea/intentable already plans a Spek page on the fork's GitHub Pages. Nothing publishes one yet.

## What Changes

- **A GitHub Actions workflow on the fork,** `.github/workflows/spek.yml`, builds Spek's viewer from the repo's `openspec/` folder: specs, active changes and archived changes, each artifact as a tab. It runs on pushes that touch `openspec/` or the workflow itself; a code-only push builds nothing.
- **Where the pages go,** on the fork's GitHub Pages (`gh-pages` branch):
  - `main` publishes at the site root, `https://natea.github.io/newenglandmusic/`;
  - each `change/<name>` branch publishes at `/changes/<name>/`;
  - a page stays when its branch is deleted, so links to it keep working (Nate's decision, 2 November 2026).
- **Draft proposals are pushed before G2 (Nate's decision, 2 November 2026).** A proposal is committed as a draft and its branch pushed to the fork before Nate's G2, so he reads it on its Spek page while reviewing. That is an exception to Igor's G2 rule, which commits a proposal only after confirmation. `AGENTS.md` records it. Pushing `change/` branches to the fork is a standing go-ahead (Nate's decision, 2 November 2026); `main` and anything upstream still need his go-ahead.
- **`bin/publish-spek-page`** puts a built page in the right folder of the site for a branch, refusing any branch name outside `main` and `change/<name>`. Django tests run it.
- **Safeguards:**
  - Spek is pinned by commit, for its action and its build;
  - branch names reach commands only through the environment;
  - publishes queue without dropping any;
  - a failed publish never fails the commit's checks, since Render deploys `main` only when every check passes;
  - a failure can never wipe the published pages: the publish runs only after a good build, and pushes only over the `gh-pages` it fetched.
- **GitHub Pages is turned on** for the fork, serving the `gh-pages` branch, with Nate's go-ahead.
- **`docs/SPEK.md`** says where the pages are, how a change gets one, and what not to put in OpenSpec files.

Out of scope:
- natea/intentable's own changes: the plans are for the newenglandmusic project and are published on its public fork (Nate, 2 November 2026);
- the bridge linking issues to Spek pages, which belongs to the spec stage.

## Capabilities

### New Capabilities

- `spec-pages`: which branches get a Spek page, at which address, when pages are made and kept, the pinned build, and the rule that drafts are published before G2.

### Modified Capabilities

(none)

## Impact

- **New files:** `.github/workflows/spek.yml`, `bin/publish-spek-page`, `docs/SPEK.md` and `core/tests/test_spek_pages.py`.
- **Changed:** `AGENTS.md`: the OpenSpec section (drafts before G2, G2 defined, the confirmation commit, host and network names kept out) and its line on pushing (`change/` branches without asking).
- **On GitHub, with Nate's go-ahead:** GitHub Pages turned on for the fork. The `gh-pages` branch is created and written only by the workflow.
- **What becomes public:** everything published is already public, since the fork is public and every `change/` branch is pushed. Pages are easier to find than branch files, so `docs/SPEK.md` asks authors to keep host and network names out of OpenSpec files.
- **Render:** the Spek run adds a check to each commit it builds, including merges to `main`. It can't fail, so it can't block a deploy, but a deploy of `main` waits for it to finish, about a minute plus any queue.
