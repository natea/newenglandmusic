## Context

The `spec` workflow runs on the fork's default branch: propose, check the draft, route, sketch on the `needs-design` route, three reviewers, revise up to four times, finish. The bridge then creates `change/<name>` from Fabro's record of the files the run added.

intentable's `add-design-feedback` adds a revision run. It is this same workflow, started on the draft branch `change/<name>` at its head, with three more inputs, `change_name`, `feedback` and `revision_scope`. So the change's folder is already in the sandbox when the run starts. The bridge commits the run's added, changed and removed files on top of the branch.

The workflow contract forbids inputs in command steps, so a script can't route on `feedback`. Only an agent prompt can read it.

## Goals / Non-Goals

**Goals:**
- A revision answers the feedback with the same reviewers and checks a new draft gets.
- A pick with changes leaves one refined sketch (Nate's decision, 11 November 2026).
- The build builds the picked sketch.

**Non-Goals:**
- A separate workflow for revisions.
- Filing split-off issues from the sandbox.
- Changing the sketch agent: a revision edits sketches in the propose step.

## Decisions

### 1. One workflow, and the propose agent picks the mode

`propose.md` gains a "Feedback" section that shows `{{ inputs.change_name }}`, `{{ inputs.feedback }}` and `{{ inputs.revision_scope }}`. The scope is `sketches` after G2. Then the agent changes only the sketches and the "Sketches" section, which is all the bridge will commit, and names the other requests in its message. The agent copies the scope into the draft as `"scope": "sketches"`. The checker then compares the change's files with the commit `install` recorded in `.intentable/base` (`git rev-parse HEAD`, before any agent ran), not `HEAD`, which Fabro's checkpoint commits move. It refuses an edit outside those, so the run fails early instead of after three reviewers. An agent that leaves out the scope skips this check, and the bridge's own check then refuses the revision, which wastes one run. It says:
- if the feedback is empty, write a new proposal as now;
- otherwise revise that change and write `revision: true`.

The draft file then carries the mode, so the scripts route on it without touching an input. The route step prints `revised` for a revision, checked before `needs-design`. The graph's unconditional `route -> fork` edge then takes it to review, so no new edge is needed.

A separate `feedback` workflow folder was the alternative. Its reviewer prompts would have had to be copies, since `@` references stay inside a folder. Two prompts in one file are easier to keep right than four copied prompts.

A propose agent could wrongly claim a revision. The bridge independently checks that the run was started as a revision of that change, so a wrong claim is refused there.

### 2. The revision edits the sketches itself

A revision doesn't run the `sketch` agent. The sketch prompt makes three new options from nothing, which is the opposite of narrowing. Instead, the propose agent edits the sketch the feedback is about, under the same safety rules, which `propose.md` repeats from `sketch.md` by reference: "follow the rules in `sketch.md`". The draft check then runs `check_sketches` as always. When the feedback picks one option and asks for changes, the agent:
- keeps that letter's file, revised;
- deletes the other two and their `options.json` entries;
- leaves `design.md`'s "Sketches" section with the one option.

Feedback with no pick (say, "make them all denser") revises all three. That is the author's choice, and it fits Nate's "rather than expanding to more variations".

### 2a. The checks come from the default branch

A revision's checkout is `change/<name>`. For #26 that branch is older than this change, so its `bin/` has no revision rules, and the old `check_draft` would refuse the change as already existing. The build workflow had the same problem ("the checkout is the change's draft branch, which can predate this workflow").

So `install` copies three files from the default branch into `.intentable/main/`, which is git-ignored, and the graph's check steps run them: `git fetch --quiet --depth 1 origin HEAD`, then `git show FETCH_HEAD:<path>` for each. The three files are the two checkers and `sketch.md`. A new draft's checkout is the default branch already, so the copies are the same files, unless the bridge's workflow test branch (`FABRO_WORKFLOW_REF`) is set. Then the checkout is that branch, but the copies are still main's. So this change can't be tried end to end before it merges, and its live check runs after the merge. `install` also runs `--record-existing` from the copy, and records `.intentable/base`. The fetch assumes the sandbox's clone has a fetchable `origin` for the public fork; live check 4.1 confirms that.

The propose prompt's revision section points at `.intentable/main/sketch.md`, not the checkout's copy.

### 3. The checker's rules for a revision

`check_draft` reads `revision`:
- A revision's change must be in `.intentable/existing-changes.txt`, recorded by `install` before the agent ran. That is the opposite of the new-draft rule.
- `new_change_folders()` must be empty.
- A revision with `state: needs-info` is refused: the bridge has no path for sending a revision back, and the feedback's questions belong in the message.

`check_sketches(required=…)` accepts the three letters, or, for a revision only, exactly one letter with its `options.json` entry and its link in `design.md`. Any other count is refused. The count is checked where sketches are required: the `--sketches` step and the last step. The first draft check (`--draft`) still requires none for a new draft. For a revision with `needs-design`, it requires the set, since a revision never passes the `--sketches` step. `check_options` follows the same set: three entries, or the one.

Labels are fixed per run by `route.json`, as now. Whether they equal the first draft's is the bridge's check, since the sandbox has no record of them.

### 4. Fidelity reads the feedback as the latest decisions

The thread already holds the feedback comments, and fidelity's decision record already includes the thread. `fidelity.md` adds one paragraph: when `.intentable/draft.json` says `revision`, check each point of the feedback in the files and each question in the message, and treat one left without a reason as blocking. A message can't list six changes and two answers in six sentences. It sums up what was done and answers the questions, and the files carry the rest. `revise.md` adds one line: keep a revision with one sketch at one.

### 5. `picked_design` in the build

The build's `workflow.toml` declares `picked_design` with an empty default. `apply.md` adds: "When `{{ inputs.picked_design }}` isn't empty, build the screens from `sketches/{{ inputs.picked_design }}.html`, and treat the other sketches as rejected." The bridge sends a single letter it checked, so the input is safe in a prompt. It is never in a command, per "No input reaches a command".

### 6. Order with `use-html-wireframes`

`use-html-wireframes` is applied and waiting on its branch. It also:
- modifies "A proposal that needs screens includes sketches";
- rewrites `sketch.md`;
- edits `revise.md`'s sketch line;
- adds `compare.html` to the required sketches.

Its hold (waiting for `add-build-workflow`) has been met. Whichever change is merged second rebases its delta onto the other's merged text. If `use-html-wireframes` is merged first, a narrowed revision also drops `compare.html`, and the checker requires it only with three sketches. This is noted as task 1.4.

## Risks / Trade-offs

- **The propose prompt does two jobs.** Its new section is the only place the mode is decided, and a muddled agent might write a new change. The checker's "no new change folder" rule and the bridge's checks both catch that, and the run fails visibly.
- **Feedback text reaches an agent.** It already does through `issue_thread`. The propose agent has no push rights, its output goes through the checker, and the bridge passes only comments from intake users.
- **A narrowed revision loses the other options.** The removed sketches stay in the branch's history, and a later feedback round can ask for them back.

## Migration Plan

Merge this change before intentable's, since the bridge only sends revision runs once its side is deployed. Until then, the new inputs are empty and the workflow behaves as now.

## Open Questions

None for this change. The bridge's open questions (who may give feedback, and picks by others) are in intentable's `add-design-feedback`.
