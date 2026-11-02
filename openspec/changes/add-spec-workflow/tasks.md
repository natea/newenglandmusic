## 1. The workflow

- [ ] 1.1 Check with `fabro validate` that a conditional edge on `outcome` routes a failed `check_reviews` to `revise` despite `on_failure="exit"`; otherwise use the `context.review_done` route from the design
- [ ] 1.2 Add `.fabro/workflows/spec/workflow.toml`: the five inputs, pull requests and run-branch pushing off, no GitHub permissions, artifacts `.intentable/result.json`, `.intentable/review.md` and `.intentable/proposal/**`
- [ ] 1.3 Add `workflow.fabro` with the graph from the design, the pinned installs and the existing-changes record
- [ ] 1.4 Write `propose.md`, `risk.md`, `spec_fit.md`, `fidelity.md` and `revise.md`
- [ ] 1.5 Add tests for "Workflow shape", "Three lenses", "Inputs used, commands without inputs", "No gate, no children", "Nothing pushed", "Reviewer prompts" and "The prompt gives the rules"

## 2. The checkers

- [ ] 2.1 Add the `spec` mode and `--draft` to `bin/check-intentable-result`: name rule, existing-changes record, `openspec validate --strict`, file cap, labels and state, message rules, and the copy to `.intentable/proposal/`
- [ ] 2.2 Add `bin/check-intentable-reviews`: rounds, reports, the limit, and `.intentable/review.md` at the end of the loop
- [ ] 2.3 Add tests for "A good result", "A name that isn't plain", "A change that already existed", "A state or another label", "Too many files", "Invalid change", "All satisfied", "One not satisfied", "The round limit", "Missing report" and "Summary written"

## 3. Guide

- [ ] 3.1 Add the `spec` section to `docs/FABRO.md`
- [ ] 3.2 Add the test for "Guide"

## 4. Live check on the Spark (with intentable's `add-spec-runs`)

- [ ] 4.1 With Nate's go-ahead, run `spec` from this branch for a test issue in `spec-review`, and check the run's artifacts, `review.md` and the agent count
- [ ] 4.2 Check that the bridge's draft branch builds its Spek page
