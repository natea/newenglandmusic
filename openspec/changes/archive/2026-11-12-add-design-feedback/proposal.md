## Why

The `spec` workflow can only write a new proposal. Once its draft is on the issue, the people reviewing it can say `/approve` and nothing else. On issue #26, Nate's feedback on the Discover page sketches went unanswered on 11 November 2026: he liked C but wanted the video playing instead of the photo, a swipe hint, a clearer way to save shows, service icons, and a site-wide header.

intentable's `add-design-feedback` makes the bridge start a revision run of this workflow for such feedback. This change is the workflow's side. Nate decided on 11 November 2026:
- anyone can give design feedback;
- a pick with changes narrows the sketches to one refined option, not three new variations;
- a request outside the issue's scope becomes its own issue;
- this is built, then #26 is its live test.

## What Changes

- **Three new inputs.** The `spec` workflow declares `change_name`, `feedback` and `revision_scope`, all empty by default. The bridge sets them only for a revision run, which targets the draft branch, so the change's folder is already checked out.
- **The propose agent revises when there's feedback.** `propose.md` gains a section with the feedback: the comments to answer, as JSON. When it isn't empty, the agent writes no new change. Instead it:
  - revises `openspec/changes/<change_name>/` from the feedback, specs and scenarios included where the feedback changes behaviour. When `revision_scope` is `sketches` (Nate already confirmed the proposal), it changes only the sketches and the design's "Sketches" section, which the checker enforces, and says in its message which requests would need the proposal changed;
  - narrows the sketches to one refined option when the feedback picks one;
  - writes `.intentable/draft.json` with `revision: true`.

  Its message says what changed. It answers each question in the feedback, and names anything out of scope as a separate issue to file. A revision can't send the issue back with a question.
- **Revisions run the current checks.** A revision's checkout is its draft branch, which can be older than these checks. So `install` copies the default branch's checkers and sketch rules into `.intentable/main/`, and the steps run those.
- **The checks know a revision.** `bin/check-intentable-result spec` accepts a revision draft only when all of these hold:
  - its change existed before the run;
  - no other change folder is new;
  - it validates.

  Whether the labels match the first draft's is the bridge's check, since the sandbox has no record of them.

  The route step sends a revision straight to review. The sketch agent doesn't run, because the propose agent edited the sketches.
- **One sketch is allowed after a pick.** With `needs-design`, the sketches are `a.html`, `b.html` and `c.html` as now, or exactly one of them when a revision narrowed to it. Its entry is in `options.json`, and `design.md` links it.
- **Fidelity checks the feedback.** The fidelity reviewer's decision record already includes the thread. For a revision it is also told to check that each point of the feedback was acted on, or answered in the message.
- **The result says it's a revision.** The result gains `revision: true`, and `files` lists the change folder after the revision, as for a draft.
- **The build knows the pick.** The `build` workflow declares the input `picked_design`, the letter of the picked sketch, empty when nothing was picked. `apply.md` tells the agent to build that sketch, ignore the others, and stop if it's missing.

Out of scope:
- the bridge's side (intentable's `add-design-feedback`);
- filing split-off issues from the workflow, which pushes nothing and has no GitHub access;
- clickable sketches, and the comparison page from `use-html-wireframes`. With one sketch left, a comparison page isn't needed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `issue-proposals`: a revision mode driven by `feedback`, its checks and route, one sketch after a pick, and fidelity checking the feedback.
- `issue-builds`: the `picked_design` input, and building the picked sketch.

## Impact

- `.fabro/workflows/spec/workflow.toml`: the three inputs.
- `.fabro/workflows/spec/workflow.fabro`: `install` copies the default branch's checks and records the base, and the check steps run the copies.
- `.fabro/workflows/spec/propose.md`: the revision section.
- `.fabro/workflows/spec/fidelity.md`: checking the feedback.
- `.fabro/workflows/spec/revise.md`: keeping a narrowed revision at one sketch.
- `bin/check-intentable-result` and `bin/check-intentable-reviews`.
- `.fabro/workflows/build/workflow.toml` and `apply.md`.
- `core/tests/test_issue_proposals.py`, `core/tests/test_issue_builds.py` and `docs/FABRO.md`.
- `use-html-wireframes`, held on its branch, modifies the same sketch requirement and rewrites `sketch.md` and `revise.md`. Whichever is merged second rebases its delta onto the other (see the design).
