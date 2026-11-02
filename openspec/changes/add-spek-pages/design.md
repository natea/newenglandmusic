## Context

See proposal.md for why. What the design rests on, checked on 2 November 2026:

- **natea/newenglandmusic:**
  - it is public, and not a GitHub fork (`fork: false`), so no fork restrictions on workflows apply;
  - Actions are enabled, with all actions allowed and SHA pinning not required;
  - its one workflow, `.github/workflows/django.yml`, runs the tests on pushes and pull requests to `main`;
  - Render deploys `main` with `autoDeployTrigger: checksPass` (`render.yaml`), which waits for every check on the commit, not only Django's: success, neutral or skipped pass;
  - GitHub Pages isn't set up, and there is no `gh-pages` branch.
- **Spek** (github.com/spekhq/spek), release v1.20.2 at commit `5542fa2dfda6c52a08fb0610a140670052056c66`:
  - its composite action checks out Spek at `spek-version` (default `master`), builds it with Node, and writes one self-contained HTML file to `output-path`;
  - it needs the repo's full history (`fetch-depth: 0`);
  - the page shows the whole `openspec/` folder: specs, active and archived changes;
  - a page is about 5 MB.
- **GitHub Actions:**
  - a push runs the workflow file in the pushed commit, so a branch gets a page only once it contains `spek.yml`;
  - a concurrency group keeps one pending run by default, and a newer one replaces it, unless `queue: max` is set;
  - a step with `continue-on-error: true` can't fail its job;
  - PyYAML reads the workflow's `on:` key as `True`.
- **The change cycle:** Igor's G2 commits a proposal only after the owner confirms it. Nate has decided otherwise for this repo (see Decisions).

## Goals / Non-Goals

**Goals:**
- Every `change/<name>` branch that contains the workflow has a page at a stable address, from its draft onward, and `main` has the site root.
- Publishing can't touch the code branches, fail or block the site's deploy, wipe published pages, run a branch name as code, or reach the upstream repository. A deploy of `main` may wait for its own publish, about a minute plus any queue.

**Non-Goals:**
- Pages for branches not named `change/<name>`.
- Linking pages from issues, which is the bridge's spec stage.
- natea/intentable's own changes.

## Decisions

**Spek is Nate's decision, and GitHub Pages follows docs/plan.md.** Nate asked for "somewhere using Spek". The plan names the fork's GitHub Pages, and Nate confirmed the public fork is where the project's plans go, with free Pages (2 November 2026).

**Change branches get pages too, beyond the plan's "every push to main" (agent's decision, made necessary by Nate's).** Nate wants to read proposals on Spek while reviewing them (G2), before they reach `main`. So `change/<name>` branches publish to `/changes/<name>/`.

**Drafts are pushed before G2 (Nate's decision, 2 November 2026).** Asked how to get a Spek view at G2, Nate chose "Push drafts before G2", an exception to Igor's G2 rule. G2 is the gate where the owner confirms a proposal.
- A proposal's artifacts are committed on its `change/` branch with "Draft" in the commit's subject, and pushed. Revisions after review are further draft commits.
- When Nate confirms, an empty commit "Confirm proposal <name> (G2)" records it, so the branch history shows when (agent's decision on the form).
- Pushing `change/` branches is a standing go-ahead (Nate's decision, 2 November 2026); `main` and the upstream still need him.
- `AGENTS.md` records all of this, defines G2, and says to keep host and network names out of OpenSpec files. With the standing go-ahead nobody checks each push, so that rule belongs where agents read it every session. `AGENTS.md`'s line on pushing `main` changes to match.
- The exception lives in nycnoise's `AGENTS.md`. intentable's change-cycle skill and rules still describe Igor's G2; for nycnoise, its own `AGENTS.md` takes precedence.

**Pages are kept (Nate's decision, 2 November 2026).** There is no `delete` trigger. A page shows its branch's last published state, normally the archived change, and later links from the bridge or dashboard keep working.

**A `gh-pages` branch with one folder per change (agent's decision).** GitHub's "deploy from Actions" Pages mode publishes a whole site per run, so each branch's run would wipe the others' pages. A `gh-pages` branch updated file by file keeps every page: `index.html` at the root for `main`, `changes/<name>/index.html` for each change, and `.nojekyll`. Pages serves the branch from its root.

**One commit on `gh-pages`, force-pushed (agent's decision).** Each page is about 5 MB, and GitHub caps a Pages site at 1 GB. Keeping every publish in history would reach that after roughly 200 publishes. Each publish amends `gh-pages`' single commit and force-pushes it, so the branch holds only the current pages. Nothing else writes that branch. Igor's rules ask before force-pushing published history; Nate's G2 of this change approves exactly this one: the workflow force-pushing `gh-pages`.

**A failure never wipes the pages (from the risk review).** With the force-push, starting `gh-pages` afresh by mistake would replace the whole site. So:
- the publish is one shell step with `set -euo pipefail`, running only `if: steps.build.outcome == 'success'`;
- it starts `gh-pages` as an orphan only when `git ls-remote --exit-code --heads origin gh-pages` exits 2, meaning no such branch; any other failure stops it;
- it pushes with `--force-with-lease=gh-pages:<the commit it fetched>`, so a push never overwrites a `gh-pages` it didn't start from.

**`bin/publish-spek-page <branch> <page> <site>` does the placing (agent's decision).**
- `main` writes `<site>/index.html`.
- `change/<name>` writes `<site>/changes/<name>/index.html`, where `<name>` matches `[A-Za-z0-9_][A-Za-z0-9._-]*`.
- Anything else exits non-zero and writes nothing.
- It always writes `<site>/.nojekyll`, and replaces only the one `index.html`, so publishing `main` can't wipe `changes/`.
- It's Python, run by Django tests through `subprocess`. The workflow's git steps around it (checking out `gh-pages`, amending, force-pushing) are plain shell, with no third-party deploy action.

**Triggers:** `push` to `main` and `change/*` with `paths: [openspec/**, .github/workflows/spek.yml]`. `change/*` matches one level, so `change/a/b` never starts a run.

**Guards:**
- `permissions: contents: write`;
- `if: github.repository == 'natea/newenglandmusic'` on the job;
- `concurrency: { group: spek-pages, cancel-in-progress: false, queue: max }`, so no publish is dropped;
- `continue-on-error: true` on every step, so a failed publish never fails the commit's checks or blocks Render. A failure shows in the Actions log, and the next push publishes again. GitHub must accept the workflow file itself, `queue:` included, which only the live check can show;
- the branch name reaches the script only through `env:` (`BRANCH: ${{ github.ref_name }}`), never pasted into a `run:` script.

**Pinned by commit (agent's decision).** `spekhq/spek@5542fa2dfda6c52a08fb0610a140670052056c66` (v1.20.2) and the same commit as `spek-version`. A tag can move, and Spek's `master` is its development branch. Spek's own composite pins its inner actions by major version, which this change doesn't control.

**Testing:** `core/tests/test_spek_pages.py`, as `SimpleTestCase`s:
- it runs `bin/publish-spek-page` into temporary site folders for the address scenarios;
- it parses `.github/workflows/spek.yml` with PyYAML (`data[True]` for `on:`) for the triggers, permissions, pins, guard, environment-only branch names, concurrency and `continue-on-error`;
- it reads `AGENTS.md` and `docs/SPEK.md`.

No test calls GitHub. The first real publishes are live checks in the tasks.

## Risks / Trade-offs

- **Drafts are public before Nate confirms them.** → His decision. The fork is already public, and drafts are labelled as such in their commits. `docs/SPEK.md` asks authors to keep host and network names out of OpenSpec files.
- **A failed publish is quiet.** The commit stays green. → The Actions log shows it, and the next publish to that branch replaces the page. The live checks look at the first ones.
- **Each page is the whole repository's OpenSpec,** about 60 changes, not just the change it's named for. → `docs/SPEK.md` says to find the change by name in the page.
- **Pages builds after a push by the job's token aren't confirmed.** → The live check watches for it. The fallback is re-saving the Pages source, or switching to "deploy from Actions" with the whole `gh-pages` tree uploaded.
- **Spek's build needs Node and a download of Spek on every run,** about a minute. → Path filters keep it to OpenSpec changes.
- **A branch that doesn't contain the workflow gets no page,** such as `change/add-triage-clarify` today. → After this change is merged to `main`, a branch gets it by merging `main` in. Until then, only branches that include this change's commits get pages.

## Migration Plan

1. Push `change/add-spek-pages` (standing go-ahead). The workflow builds and creates `gh-pages` with `changes/add-spek-pages/`.
2. With Nate's go-ahead, turn Pages on for `gh-pages` at `/`, and check the page.
3. After G4: archive, merge into `main`, and push `main` with his go-ahead, which also deploys the site on Render. Check that the root page appears and `changes/add-spek-pages/` is still served. Then `change/add-triage-clarify` merges `main` in and is pushed, and gets its page. These steps come after the archive, so they are follow-ups, not tasks.

**Rollback:** turn Pages off, delete `gh-pages`, and remove the workflow file. Pages may serve cached copies for a short while.

## Open Questions

none
