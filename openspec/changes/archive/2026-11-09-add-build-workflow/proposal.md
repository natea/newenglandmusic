## Why

Once Nate confirms a proposal at gate G2, by commenting `/approve` on its issue, the intentable bridge starts the fork's `build` workflow for it. That is intentable's `add-build-runs`, confirmed by Nate on 9 November 2026 and built. This repository has no `build` workflow yet, so the first approval, on Mark's issue #14 (`export-venues-csv`), would fail to start. This change adds the workflow, following the contract `add-build-runs` sets out. With it, the loop can build a confirmed change and hand Nate a pull request.

## What Changes

- **A `build` workflow** in `.fabro/workflows/build/`, started by the bridge for an issue G2 moved to `building`. It takes the five issue inputs and `change_name`. Its run targets the change's draft branch, `change/<name>`, at the commit that records G2.
- **Every agent step is Claude Code through ACP, on Nate's Max subscription** (Nate's decisions D8 and 9 November 2026), like the other workflows.
- **Setup.** One command step installs what the site's tests need, as CI does:
  - Claude Code, its ACP adapter and `openspec`, at pinned versions;
  - Python 3.11 and the dev requirements, through `uv`;
  - a local Postgres;
  - Chromium for the browser test;
  - the compiled CSS.

  It also records the commit the run targeted, so later checks know what the run added.
- **Apply, one task group at a time.** Claude Code applies the change's `tasks.md`, group by group, following the change's proposal, design and specs. It is given the change's name and the issue's number and title, not the thread: the confirmed proposal is its instruction. Each group is one commit, with its boxes ticked in the same commit, made only once the suite passes (rule G3).
  - A task only a person can do, a check by hand in a browser or a live check against an outside system, is left unticked and named for Nate in the pull request and the message. That departs from G3's every-box-ticked rule, and is the author's decision for G2 (design).
  - If a group can't be made to pass, the agent discards it, stops, and says why.
  - If the proposal leaves a decision open, it stops and asks the question in its message. No build waits for an answer, as with every run in this repository (Nate's decision, 2 November 2026). Nate writes the answer into the change on its branch, then retries.
- **Refactor.** If every group was committed, a second agent makes a refactoring pass, following the refactoring rules this workflow carries with it. It makes one more commit, only on green, and none if there is nothing worth changing. It only reports what the rules leave to the owner (dead code, layering, new groupings), in the summary for Nate.
- **Check and write the result.** A last command step:
  - runs the whole suite once more;
  - checks the run's commits: no merge commits, no closing keywords in their messages, and nothing under `.github/` or `.fabro/`, nor `bin/publish-spek-page`. Fabro's own checkpoint commits pass when empty;
  - for a complete build, checks every box in the change's `tasks.md` is ticked, apart from the tasks left for a person;
  - writes `.intentable/result.json` with no labels and no state, the agent's `message`, the `outcome` (`complete` or `stopped`) and the `change`;
  - writes `.intentable/pull-request.md` for the pull request: the agents' summary, and any task left for a person.

  A broken rule fails the run, which the bridge reports.
- **The run branch is pushed, and no pull request is opened.** `[run.run_branch] push = true` and `[run.pull_request] enabled = false`. The bridge checks the run branch again before it fast-forwards the draft branch and opens the pull request itself. This differs from the other workflows, which push nothing (Nate's decision, 2 November 2026, for runs that only read the code). Nate confirmed this one at G2 of `add-build-runs`, on 9 November 2026.
- **Self-contained.** The checkout is the draft branch, which was cut from `main` when the spec ran. It can predate this change, as #14's does. So nothing in the workflow runs a script from the checkout: its checks are inline in `workflow.fabro`, and its rules are in its prompts.
- **A stopped build is reported, not published** (Nate's decision, 9 November 2026). Its result says `stopped`, with the agent's reason in its message; the bridge posts it on the issue and publishes nothing.
- **`.gitignore`** stops ignoring `.fabro/workflows/build/`, which its packaging line `build/` matched.
- **`docs/FABRO.md`** describes the workflow.

Out of scope:
- the bridge's part: G2, starting the run, checking and publishing its work, the pull request. That is intentable's `add-build-runs`;
- the sandbox preview, `preview-ready` and G4, which come next;
- building an issue that waits on a sketch pick.

**Dependencies:**
- **intentable's `add-build-runs`** is built and waits for this workflow for its live check.
- **To test before merging,** the bridge reads workflows from `change/add-build-workflow` (`FABRO_WORKFLOW_REF`). This branch is cut from `main`, so it carries `main`'s other workflows.
- **The fork's `main` ruleset** must protect `main` against force-push and deletion before that live check, as `add-build-runs` requires. The run branch is pushed with a token that acts as Nate, so blocking the sandbox from pushing `main` waits for the Intentable GitHub App, a later change (Nate's decision, 9 November 2026).

## Capabilities

### New Capabilities

- `issue-builds`: the `build` workflow: its inputs, target and settings, the apply and refactor steps, the rules its commits follow, the checks before its result, and the result and summary it leaves for the bridge.

### Modified Capabilities

None. The other workflows and their checker are unchanged.

## Impact

- **Code:** `.fabro/workflows/build/` (`workflow.toml`, `workflow.fabro`, `apply.md`, `refactor.md`), a line in `.gitignore`, and tests in `core/tests/test_issue_builds.py`.
- **Docs:** `docs/FABRO.md`.
- **Fabro:** no new secret. The vault's GitHub token already has Contents write, which pushing the run branch needs. It has no Workflows permission, so GitHub refuses a push that changes `.github/workflows/`.
- **Sandbox time:** a build is long. The bridge gives build sandboxes a 360-minute lifetime (`add-build-runs`).
