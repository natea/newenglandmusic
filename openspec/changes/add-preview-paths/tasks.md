## 1. The record and the result

- [ ] 1.1 In `apply.md`'s "Your record", add `preview` to the example and its rule: the pages a reviewer should open to see or test the change, each a path from the site's root and what to look at, at most 8, for someone who isn't a developer; leave it out when nothing is visible on the site. In `refactor.md`, keep `preview` true if a page moves.
- [ ] 1.2 In `workflow.fabro`'s finish step, check `preview` (a list of at most 8; each `path` matches a plain site path; each `check` is 1 to 120 characters) and copy it into `result.json` when present. Verify with tests in `core/tests/test_issue_builds.py` for "Pages to check", "A page that isn't on the site" and "Pages in the result", and that the existing scenarios still hold.

## 2. Live check

- [ ] 2.1 With Nate's G4: merge, and on the next build whose change shows on the site, check that its result carries `preview`, and, once a preview change is live, that the preview's comment links those pages.
