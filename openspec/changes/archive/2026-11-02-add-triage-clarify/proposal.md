## Why

The intentable bridge now runs on the DGX Spark and starts a `triage` run when someone on its intake list opens an issue on natea/newenglandmusic, and a `clarify` run when they reply to an issue waiting for information. Neither workflow exists yet, so every issue gets "the agent couldn't start" (issue #9, 2 November 2026). This change adds both, so requests are sorted and clarified in the issue's comments, as docs/plan.md describes.

## What Changes

- **A `triage` workflow** in `.fabro/workflows/triage/`:
  - An agent, Claude Code through ACP on Nate's Max subscription, reads the issue and the site's code, in the OpenSpec explore stance: curious, investigating, never prescribing or building.
  - It gives first-guess labels from Conor Luddy's taxonomy: type, clarity, risk, blast radius and size.
  - Then:
    - an issue clear enough to write up (clarity 4 or more) moves to `spec-review`, with a short summary of what will be built;
    - a less clear one moves to `needs-info`, with one focused question;
    - a grey-area issue, where it's unclear whether the behaviour belongs in the site's spec, moves to `parked`, with the reason, for Nate to decide. That is the plan's meaning of `parked` (Nate's decision, 2 November 2026).
- **A `clarify` workflow** in `.fabro/workflows/clarify/`:
  - The same agent reads the whole thread and the code, and judges clarity afresh. The bridge doesn't pass an issue's current labels.
  - It either asks the next single question (`needs-info`), or moves the issue to `spec-review` with its summary.
- **Every run ends with its result. Nobody's answer is waited for (Nate's decision, 2 November 2026).** A question is the run's result, posted by the bridge. The reply starts a fresh `clarify` run, so no sandbox waits on a person.
- **Both read the code and push nothing (Nate's decision, 2 November 2026).**
  - They push no branch and open no pull request. Fabro gives the sandbox read-only git access.
  - The agent writes only its result file, inside its sandbox.
- **A result checker,** `bin/check-intentable-result`, runs as each workflow's last step. It refuses:
  - any result the bridge would refuse;
  - labels for later stages: priority, `needs-design`, `ai-shippable`;
  - a state that doesn't fit the clarity;
  - a `needs-info` message that asks more or less than one question, or any message that mentions anyone or runs too long.

  A bad result then fails the run instead of reaching the issue.
- **Both follow the bridge's workflow contract:**
  - the five issue inputs declared;
  - `on_failure="exit"`;
  - no issue input in a command script;
  - no child workflows, and every file Fabro reads for the workflow kept in its folder;
  - `.intentable/result.json` collected as an artifact and kept out of git.
- **`docs/FABRO.md`** describes both workflows and how to try them on a branch.

Out of scope:
- the spec, design and build stages, and Nate's gates G2 and G4;
- priority, `needs-design` and `ai-shippable`, which later stages set;
- `[run.scm]` in `.fabro/project.toml`, which Fabro never sends, for a change of its own;
- publishing these artifacts with Spek, which is the separate change `add-spek-pages`.

Depends on, for the live check only: an intentable change that makes the bridge's test-branch setting, `FABRO_WORKFLOW_REF`, also set the run's code to that branch (Nate's decision, 2 November 2026). Without it, a test run uses `main`'s code, which has no checker until this change is merged.

## Capabilities

### New Capabilities

- `issue-triage`: what the `triage` and `clarify` workflows do with an issue: the labels they give, when they ask, write up or park, how they leave their result, and what they may not touch.

### Modified Capabilities

(none)

## Impact

- **New files:**
  - `.fabro/workflows/triage/` and `.fabro/workflows/clarify/`, each with `workflow.toml`, `workflow.fabro` and the agent's `prompt.md`;
  - `bin/check-intentable-result`;
  - `core/tests/test_issue_triage.py`.
- **Changed:** `.gitignore` (adds `.intentable/`) and `docs/FABRO.md`.
- **Uses, unchanged:**
  - the `daytona` environment on the Spark's Fabro, with its Claude subscription token;
  - the intentable bridge's label set and allowed moves.
- **Takes effect** once these workflows are on natea/newenglandmusic's default branch, which the bridge reads. Pushing `main` there also makes Render deploy the site, as every push to `main` does.
- **Cost:** each issue and reply from the intake list then costs one Claude Code session on the Max subscription, and a Daytona sandbox for a few minutes.
