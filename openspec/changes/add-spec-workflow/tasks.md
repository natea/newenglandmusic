## 1. The workflow

- [ ] 1.1 Check with `fabro validate` that a conditional edge on `outcome` routes a failed `check_reviews` to `revise` despite `on_failure="exit"`; otherwise use the `context.review_done` route from the design
- [ ] 1.2 Add `.fabro/workflows/spec/workflow.toml`: the five inputs, pull requests and run-branch pushing off, no GitHub permissions, artifacts `.intentable/result.json`, `.intentable/review.md` and `.intentable/proposal/**`
- [ ] 1.3 Add `workflow.fabro` with the graph from the design, every agent through ACP, the pinned installs and the existing-changes record
- [ ] 1.4 Write `propose.md`, `risk.md`, `spec_fit.md`, `fidelity.md` and `revise.md`
- [ ] 1.5 Add tests for "Workflow shape", "Every agent through ACP", "Inputs used, commands without inputs", "No gate, no children, references inside", "Nothing pushed", "Three lenses", "Decision record and bridge comments", "Reviewer prompts", "Revise prompt" and "The prompt gives the rules"

## 2. The checkers

- [ ] 2.1 Add the `spec` mode and `--draft` to `bin/check-intentable-result`:
  - read `.intentable/draft.json`;
  - check the name rule, and the existing-changes record with archive dates stripped;
  - run `openspec validate --strict`;
  - check the bounds: file cap, text only, skipped folder names;
  - check labels, state and the message rules;
  - without `--draft`, empty and fill `.intentable/proposal/` and write the result.
- [ ] 2.2 Add `bin/check-intentable-reviews`: rounds, reports and revise notes kept per round, the limit, and `.intentable/review.md` with its fixed first line
- [ ] 2.3 Add a fake `openspec` executable for the tests, placed first on `PATH`
- [ ] 2.4 Add tests for "Draft check reads the draft file", "A good result", "Only the final text", "A name that isn't plain", "A change that already existed", "No change folder", "A state or another label", "Too many files", "A file Fabro wouldn't collect", "Invalid change", "A message that mentions someone", "All satisfied", "One not satisfied", "The round limit", "Missing report", "Summary written" and "Summary of a review not passed"

## 3. Guide

- [ ] 3.1 Add the `spec` section to `docs/FABRO.md`
- [ ] 3.2 Add the test for "Guide"

## 4. Live check (with intentable's `add-spec-runs`)

- [ ] 4.1 With Nate's go-ahead, run `spec` from this branch for a test issue in `spec-review`; check the run's artifacts, `review.md`, the agent count, and the elapsed time against the sandbox lifetime
- [ ] 4.2 Check that the bridge's draft branch builds its Spek page; that page is kept, like every page
