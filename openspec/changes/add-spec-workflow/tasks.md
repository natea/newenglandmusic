## 1. The workflow

- [ ] 1.1 Check with `fabro validate` that a conditional edge on `outcome` routes a failed `check_reviews` to `revise` despite `on_failure="exit"`; otherwise use the `context.review_done` route from the design
- [ ] 1.2 Add `.fabro/workflows/spec/workflow.toml`: the five inputs, pull requests and run-branch pushing off, no GitHub permissions, artifacts `.intentable/result.json`, `.intentable/review.md` and `.intentable/proposal/**`
- [ ] 1.3 Add `workflow.fabro` with the graph from the design, every agent through ACP, the pinned installs (Impeccable from `pbakaus/impeccable` included; check the version can be pinned) and the existing-changes record
- [ ] 1.4 Commit Impeccable's design context from the main checkout: `.impeccable/config.json`, `design.json`, `surfaces/`, `mocks/` and `PRODUCT.md` (`DESIGN.md` is already committed); not `config.local.json`, `hook.cache.json`, `questions/` or `review/`; check the JSON parses
- [ ] 1.5 Write `propose.md`, `sketch.md` (system fonts and inline styles only), `risk.md`, `spec_fit.md`, `fidelity.md` and `revise.md`
- [ ] 1.6 Add tests for "Workflow shape", "Sketch step only for needs-design", "Every agent through ACP", "Inputs used, commands without inputs", "No gate, no children, references inside", "Nothing pushed", "Three lenses", "Decision record and bridge comments", "Reviewer prompts", "Revise prompt" and "The prompt gives the rules"

## 2. The checkers

- [ ] 2.1 Add the `spec` mode and `--draft` to `bin/check-intentable-result`:
  - read `.intentable/draft.json`;
  - check the name rule, and the existing-changes record with archive dates stripped;
  - run `openspec validate --strict`;
  - check the bounds: file cap, text only, skipped folder names;
  - check labels, state and the message rules;
  - `--sketches`: the sketches are there, linked from `design.md`, and pass the allowlist; `--draft` checks only the safety of any sketches present;
  - the labels against `.intentable/route.json`;
  - without `--draft`, empty and fill `.intentable/proposal/`, copy the summary to `.intentable/review.md`, and write the result with `reviewed` and `files`.
- [ ] 2.2 Add `bin/check-intentable-reviews`: rounds, reports and the revise notes filed with the round they answer, the limit, and the summary with its fixed first line and the outcome
- [ ] 2.3 Add a fake `openspec` executable for the tests, placed first on `PATH`
- [ ] 2.4 Add tests for "Not ready", "A send-back that breaks the rules", "Summary beside the result", "Draft check reads the draft file", "Sketches required with needs-design", "Unsafe sketch caught before review", "A sketch lost in revise", "First draft check without sketches", "A sketch with a script", "A sketch that calls out", "A safe sketch", "Revise adds needs-design", "A good result", "Only the final text", "A name that isn't plain", "A change that already existed", "No change folder", "A state or another label", "Too many files", "A file Fabro wouldn't collect", "Invalid change", "A message that mentions someone", "All satisfied", "One not satisfied", "The round limit", "Missing report", "Summary written" and "Summary of a review not passed"

## 3. Sketches on the Spek page

- [ ] 3.1 Copy a change's regular `sketches/*.html` files in `bin/publish-spek-page`, replacing that change's `sketches/` folder whole, and add the Content-Security-Policy tag at the start of each, after any doctype
- [ ] 3.2 Add tests for "Sketches published", "A sketch removed", "A link instead of a file", "Policy added", "A sketch with no head" and "No sketches on main"

## 4. Guide

- [ ] 4.1 Add the `spec` section to `docs/FABRO.md`
- [ ] 4.2 Add the test for "Guide"

## 5. Live check (with intentable's `add-spec-runs`)

- [ ] 5.1 With Nate's go-ahead, run `spec` from this branch for issue #9, already in `spec-review` (Nate's choice, 2 November 2026); check the run's artifacts, `review.md`, the agent count, the elapsed time against the sandbox lifetime, and, if it needs design, whether Impeccable's decision step runs unattended without a browser
- [ ] 5.2 Check that the bridge's draft branch builds its Spek page; that page is kept, like every page
