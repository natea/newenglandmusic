## Why

The `triage` and `clarify` workflows move an issue to `spec-review` once it is clear enough to write up, and tell the person who asked: "Next, this will be written up as a proposal for Nate to review before anything is built." Nothing writes it up yet. Step 4 of intentable's plan does that: the agent writes an OpenSpec proposal, three fresh reviewers check it for risk, spec fit and fidelity, and Nate reads it before confirming it (gate G2). This change adds the workflow that does it.

## What Changes

- **A `spec` workflow** in `.fabro/workflows/spec/`, started by the intentable bridge for an issue in `spec-review`. It takes the same five issue inputs as `triage` and `clarify`.
  - **Propose.** Claude Code, through ACP, reads the issue thread and the site's code. It then writes a complete OpenSpec change for it: proposal, delta specs, design and tasks. It uses the `openspec` CLI at a pinned version and follows this repository's `openspec/config.yaml` and `AGENTS.md`.
  - **Review.** Three reviewers run in parallel, each a fresh agent with one lens: risk, spec fit and fidelity. The lenses are the ones in the `dev-review-proposal` skill. Fidelity is checked against what the person who asked said in the thread and against this repository's recorded rules. Each reviewer writes a report and edits nothing.
  - **Revise.** A fourth agent applies every blocking finding, plus the non-blocking ones it agrees with. It records each finding it doesn't apply, with the reason. Then the three reviewers run again on the revised text.
  - The loop stops when all three are satisfied in the same round, or after three rounds. If it stops at the limit, the run still ends with the draft, marked as not passed by the reviewers, so Nate sees the open findings (decision taken without Nate, see design).
- **The run pushes nothing (Nate's decision, 2 November 2026: runs read the code and push nothing).** Like `triage` and `clarify`, it opens no pull request, pushes no run branch and asks Fabro for no GitHub permissions. The last step copies the finished change into `.intentable/proposal/`, which Fabro collects as artifacts. The intentable bridge commits it from there to a `change/<name>` branch on the fork, under its own change. That push gives the draft its Spek page.
- **The result.** `.intentable/result.json` names the change and gives a plain-words message for the issue. It may add the `needs-design` label when the proposal needs screens sketched, which the plan's next step uses. It gives no state, so the issue stays in `spec-review` until Nate confirms. `.intentable/review.md` sums up the review: rounds, blocking findings and their fixes, findings not applied with their reasons, and open questions. The bridge uses it as the draft commit's message.
- **The result checker** gains a `spec` mode, `bin/check-intentable-result spec`. It fails the run when:
  - the change name isn't a plain kebab-case name;
  - the change already exists in `openspec/changes/` or its archive on the run's base;
  - the change doesn't pass `openspec validate --strict`;
  - the change has too many files for Fabro to collect;
  - the result names a state, or any label other than `needs-design`;
  - the message breaks the existing message rules.
- **`docs/FABRO.md`** describes the workflow.

Out of scope:
- the bridge's part (starting the run, committing the draft, posting the link), which is the intentable change `add-spec-runs`;
- recording Nate's G2 through the issue, and any move out of `spec-review`;
- revising a draft after Nate comments on it;
- Impeccable sketches for `needs-design`.

## Capabilities

### New Capabilities

- `issue-proposals`: what the `spec` workflow does with an issue in `spec-review`: write an OpenSpec change, have three reviewers pass it, revise it, and leave the draft and a result for the bridge, pushing nothing itself.

### Modified Capabilities

(none)

## Impact

- **New files:**
  - `.fabro/workflows/spec/`, with `workflow.toml`, `workflow.fabro` and one prompt each for propose, the three lenses and revise;
  - `bin/check-intentable-reviews`, which reads the three reports and decides whether to run another round;
  - `core/tests/test_issue_proposals.py`.
- **Changed:** `bin/check-intentable-result` gains the `spec` mode; `docs/FABRO.md`.
- **Cost:** a run is up to 1 propose, 9 review and 3 revise agent sessions on Nate's Anthropic key, inside one sandbox and within the bridge's sandbox lifetime (three hours).
