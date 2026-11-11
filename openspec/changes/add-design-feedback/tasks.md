## 1. The spec workflow's revision mode

- [x] 1.1 Declare `change_name`, `feedback` and `revision_scope` in `.fabro/workflows/spec/workflow.toml`, each defaulting to an empty string. Add the "Feedback" section to `propose.md`: revise the named change, narrow a pick with changes to one sketch following `sketch.md`'s rules, answer questions, name out-of-scope requests, and write `revision: true`. Verify with:
  - "Inputs used, commands without inputs";
  - "The propose prompt has the revision section", "The prompt asks for answers", "The prompt limits a revision after G2", "A sketch-only revision that changes the spec" (with a checkpoint commit in the fixture) and "The prompt gives a revision's exceptions", keeping "The prompt gives the rules" passing;
  - "Prompts keep one sketch", for the `propose.md` half.
- [x] 1.1a Make `install` copy the two checkers and `sketch.md` from the default branch into `.intentable/main/`, and point every check step and the revision section at those copies. Also record `.intentable/base`, and run `--record-existing` from the copy. Verify with "A revision on a branch cut before this change" (a checker test run on a fixture checkout) and "Check steps run the copies". Update "Workflow shape" and the three scenarios of "Sketches are checked as soon as they are made" for the copied path.
- [x] 1.2 In `bin/check-intentable-result`, add the revision rules to `check_draft`, the one-sketch case to `check_sketches`, and `revision` to the result. Verify with:
  - "A revision of an existing change" and "A revision that makes a new change";
  - "A revision that asks a question back" and "An unsafe sketch in a revision";
  - "One sketch after a pick", "Two sketches" and "Two sketches at the first check", with `check_options` accepting one entry;
  - "A revision's result".

  Keep "A change that already existed", "Sketches required with needs-design" and "A good result" passing.
- [x] 1.3 Make the route step print `revised` for a revision, checked before `needs-design`. Add the feedback paragraph to `fidelity.md` and the one-sketch line to `revise.md`. Verify with:
  - "A revision goes straight to review" and "A revision skips the sketch step";
  - "Fidelity checks each point of the feedback", keeping "Decision record and bridge comments" passing;
  - "Prompts keep one sketch", for the `revise.md` half.

  Keep "Workflow shape" (as updated in 1.1a), "Sketch step only for needs-design" and "Revise prompt" passing.
- [x] 1.4 (Not needed: this change merges first, so `use-html-wireframes` rebases onto it.) If `use-html-wireframes` was merged first, rebase this change onto it. Restate the sketch requirement's delta on the merged text, and require `compare.html` only with three sketches, and make sure "Sketches are low-fidelity wireframes" and "Revise keeps sketches plain" also bind sketches the propose agent edits in a revision. Rerun the workflow tests.

## 2. The build's pick

- [x] 2.1 Declare `picked_design` in `.fabro/workflows/build/workflow.toml`, and add the picked-sketch paragraph to `apply.md`. Verify with "Declared inputs", "The prompts name the change, not the thread" and "The apply prompt names the pick", keeping "Commands without inputs" passing.

## 3. Guide

- [ ] 3.1 Describe the revision mode, the one-sketch rule and `picked_design` in `docs/FABRO.md`, and check that the configuration test for the guide still passes.

## 4. Live check (with Nate's go-ahead, together with intentable's)

- [ ] 4.1 With both sides deployed, confirm issue #26's revision run:
  - it skips the sketch step and leaves only a refined `sketches/c.html`;
  - its message answers whether the show picker appears always or only after a right swipe;
  - its message names the site-wide header as its own issue;
  - the three reviewers pass it;
  - `install`'s fetch of the default branch worked in the sandbox.
