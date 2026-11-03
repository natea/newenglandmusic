## Why

The `triage` and `clarify` workflows move an issue to `spec-review` once it is clear enough to write up, and tell the person who asked: "Next, this will be written up as a proposal for Nate to review before anything is built." Nothing writes it up yet. Step 4 of intentable's plan does that: the agent writes an OpenSpec proposal, three fresh reviewers check it for risk, spec fit and fidelity, and Nate reads it before confirming it (gate G2). This change adds the workflow that does it.

## What Changes

- **A `spec` workflow** in `.fabro/workflows/spec/`, started by the intentable bridge for an issue in `spec-review`. It takes the same five issue inputs as `triage` and `clarify`.
  - **Every agent step is Claude Code through ACP, on Nate's Max subscription** (Nate's decision D8), like `triage` and `clarify`; none is a Fabro prompt stage, which would bill the API key.
  - **Propose.** Claude Code reads the issue thread and the site's code. It then writes a complete OpenSpec change for it: proposal, delta specs, design and tasks. It uses the `openspec` CLI at a pinned version and follows this repository's `openspec/config.yaml` and `AGENTS.md`.
  - **Review.** Three reviewers run in parallel, each a fresh agent with one lens: risk, spec fit and fidelity. The lenses are the ones in the `dev-review-proposal` skill. Fidelity is checked against what the person who asked said in the thread and against this repository's recorded rules. Each reviewer writes a report and edits nothing. From the second round on, each is told what revise changed.
  - **Revise.** A fourth agent applies every blocking finding, plus the non-blocking ones it agrees with. It writes down how it fixed each finding, or why it didn't apply it, and never renames the change. Then the three reviewers run again on the revised text.
  - The loop stops when all three are satisfied in the same round, or after five rounds. If it stops at the limit, the run still ends with the draft, marked as not passed by the reviewers, so Nate sees the open findings (Nate's decision, 2 November 2026).
- **Sketches, when the proposal needs screens** (Nate's decision, 2 November 2026). When the draft is labelled `needs-design`, one more agent runs Impeccable's decision step before the review. It writes three self-contained HTML sketches into the change's `sketches/` folder, with each option's label, thesis and risk, and the design links them. The reviewers review them with the rest of the change, so Nate sees the sketches at G2. Choosing one is a later stage for Sooz or Mark. They are static pictures in a browser: clicks go nowhere (see the design's open question). They are published beside the change's Spek page, each with a thumbnail rendered in a job that holds no write token, for the bridge's issue comment. Impeccable's design context is committed with this change, so the sandbox has it: the `.impeccable/` files and `PRODUCT.md`, both as Nate agreed (`DESIGN.md` is already committed).
- **An issue that isn't ready goes back** (Nate's decision, 2 November 2026). If the agent finds the issue isn't clear enough to write up, it writes no change and ends with `needs-info`, a clarity of 1 to 3, and one question for the person who asked, with no sketch or review.
- **The run pushes nothing (Nate's decision, 2 November 2026: runs read the code and push nothing).** Like `triage` and `clarify`, it opens no pull request, pushes no run branch and asks Fabro for no GitHub permissions. The last step, and only the last, writes the result, which Fabro collects as an artifact. The intentable bridge commits the change, from Fabro's record of the files the run changed, to a `change/<name>` branch on the fork, under its own change. That push gives the draft its Spek page.
- **The result.** While the run works, the change's name and message live in `.intentable/draft.json`. At the end, `.intentable/result.json` names the change, gives a plain-words message for the issue, says whether the reviewers passed it (`reviewed`), and lists the change's files. It may add the `needs-design` label when the proposal needs screens sketched, which the plan's next step uses. It gives no state, so the issue stays in `spec-review` until Nate confirms. `.intentable/review.md` starts with a fixed line, `Passed by the reviewers after <n> round(s).` or `Not passed by the reviewers after <n> rounds.`, then sums up the review: rounds, blocking findings and their fixes, and findings not applied with their reasons. The bridge uses it as the draft commit's message.
- **The result checker** gains a `spec` mode, `bin/check-intentable-result spec`. It fails the run when:
  - the change name isn't a plain kebab-case name;
  - the change already exists in `openspec/changes/` or its archive on the run's base;
  - the change doesn't pass `openspec validate --strict`;
  - the change has too many files for Fabro to collect, a file that isn't text, or a folder name Fabro skips;
  - a draft with a change names a state, or any label other than `needs-design`;
  - a `needs-design` change lacks its sketches, a sketch fails the HTML allowlist, or the labels changed after the sketch step was decided;
  - the message breaks the existing message rules.
- **`docs/FABRO.md`** describes the workflow.

Out of scope:
- the bridge's part (starting the run, committing the draft, posting the link), which is the intentable change `add-spec-runs`;
- recording Nate's G2 through the issue, and any move out of `spec-review` other than the send-back;
- revising a draft after Nate comments on it;
- Sooz or Mark picking a sketch.

## Capabilities

### New Capabilities

- `issue-proposals`: what the `spec` workflow does with an issue in `spec-review`: write an OpenSpec change, have three reviewers pass it, revise it, and leave the draft and a result for the bridge, pushing nothing itself.

### Modified Capabilities

- `spec-pages`: a change's sketches are published beside its page.

## Impact

- **New files:**
  - Impeccable's design context: `.impeccable/` (config, design, surfaces, mocks) and `PRODUCT.md`;
  - `.fabro/workflows/spec/`, with `workflow.toml`, `workflow.fabro` and one prompt each for propose, sketch, the three lenses and revise;
  - `bin/check-intentable-reviews`, which reads the three reports and decides whether to run another round;
  - `core/tests/test_issue_proposals.py`.
- **Changed:** `bin/check-intentable-result` gains the `spec` mode; `bin/publish-spek-page` also publishes a change's sketches and renders thumbnails; `.github/workflows/spek.yml` gains a `thumbnails` job; `docs/FABRO.md`; `core/tests/test_spek_pages.py`.
- **Usage:** a run is up to 1 propose, 1 sketch, 15 review and 4 revise agent sessions on Nate's Max subscription, inside one sandbox and within the bridge's sandbox lifetime (three hours).
