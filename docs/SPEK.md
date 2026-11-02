### spek pages

[Spek](https://github.com/spekhq/spek) turns this repo's `openspec/` folder into a single page you can read in a browser: the specs, and every active and archived change, each with its proposal, design, tasks and spec deltas as tabs. The `Spek pages` workflow (`.github/workflows/spek.yml`) publishes those pages on this repo's GitHub Pages site.

#### where they are

- **The site:** <https://natea.github.io/newenglandmusic/> shows `main`.
- **A change:** <https://natea.github.io/newenglandmusic/changes/<name>/> shows the branch `change/<name>`, for example `changes/add-triage-clarify/`.

Each page shows the whole repository's OpenSpec as it is on that branch, not only one change, so find the change by its name in the page's list of changes.

#### when they're published

- **A change branch** publishes whenever a push to `change/<name>` touches `openspec/` or the workflow. Proposals are pushed as drafts before the owner confirms them (G2), so the page is there to review from the first draft (`AGENTS.md`).
- **`main`** is rebuilt once a day, and whenever someone starts the workflow from the repo's Actions tab ("Spek pages", "Run workflow"). It never runs on a push to `main`, so Render's deploy never waits for it. The root page can be up to a day behind `main`.
- **A branch gets a page only once it contains the workflow file,** `.github/workflows/spek.yml`, from `main`. An older branch gets it by merging `main` in.
- **Pages stay after a branch is deleted,** showing its last published state, normally the archived change, so links to them keep working.

A failed publish never fails a commit's checks; look at the "Spek pages" runs in the Actions tab. The next push, or the next day for `main`, publishes again.

#### what not to put in openspec files

Pushed branches and their Spek pages are public, and pages are easy to find. Keep host and network names out of OpenSpec files: no machine names, tailnet or internal addresses, tokens or other secrets.
