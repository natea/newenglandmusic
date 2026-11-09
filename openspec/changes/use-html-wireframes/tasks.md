## 1. Sketch step

- [ ] 1.1 Pick effective-html's commit (the latest on its default branch when this is applied), read `skills/html-wireframe/SKILL.md` at it, and record the full SHA in the design
- [ ] 1.2 In `workflow.fabro`, replace Impeccable's clone and plugin install in `install` with the pinned fetch of effective-html and the copy of `skills/html-wireframe` into `~/.claude/skills/`, and change the `sketch` step's label and the install comment
- [ ] 1.3 Rewrite `sketch.md` per the design: the `html-wireframe` skill, unattended; three structurally different files; the existing safety rules; grayscale and labelled placeholders; drawn boxes for form controls; 1440×900 with a 390px reflow; `options.json` mapping; `PRODUCT.md` and the templates, not `DESIGN.md` or `.impeccable/`
- [ ] 1.4 Update the install check in `core/tests/test_issue_proposals.py` and add tests for "Wireframe skill pinned" and "The sketch prompt asks for wireframes"; keep "Workflow shape", "Sketch step only for needs-design", "Sketches required with needs-design" and "Options for each sketch" passing
- [ ] 1.5 Run `fabro validate` on the workflow and `openspec validate use-html-wireframes --strict`

## 2. Docs

- [ ] 2.1 Update the sketch step in `docs/FABRO.md`

## 3. Merge

- [ ] 3.1 With Nate's G4 and go-ahead to push `main`, merge to the fork's `main`

## 4. Live check

- [ ] 4.1 With Nate's go-ahead, run `spec` for a `needs-design` issue (from the merged `main`, or a test branch through `FABRO_WORKFLOW_REF`)
- [ ] 4.2 Check that the agent used `html-wireframe`, that the three sketches are grayscale and differ in structure, that `check_sketches` passed, and that the thumbnails reach the Spek page; tick `add-spec-workflow` 5.3 with the same run
- [ ] 4.3 Archive `add-spec-workflow`, then this change
