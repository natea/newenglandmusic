## 1. Sketch step

- [ ] 1.1 Pick effective-html's commit (the latest on its default branch when this is applied), read `skills/html-wireframe/SKILL.md` at it, and record the full SHA in the design
- [ ] 1.2 In `workflow.fabro`, replace Impeccable's clone and plugin install in `install` with the pinned fetch of effective-html and the copy of `skills/html-wireframe` into `~/.claude/skills/`, and change the `sketch` step's label and the install comment
- [ ] 1.3 Rewrite `sketch.md` per the design: the `html-wireframe` skill, unattended; three structurally different static files, no `:target` panels inside `a.html`, `b.html` and `c.html`; the existing safety rules; the allowed elements and attributes and the likely refusals; grayscale and labelled placeholders; drawn boxes for form controls; 1440×900 with a 390px reflow and the viewport `<meta>`; the `options.json` mapping, with `thesis` as why the structure might suit; `PRODUCT.md`, the "Audience, job and content" sections of `.impeccable/surfaces/` where there is one (a new page or the venue surface has none) and the templates, without naming `DESIGN.md`, `.impeccable/design.json` or `.impeccable/mocks/`
- [ ] 1.4 Add the line to `revise.md`: an edited sketch stays a grayscale wireframe under the same rules, with the viewport `<meta>` allowed, and its panel in `compare.html` changes with it
- [ ] 1.5 Add to `sketch.md` the comparison page per the design: written after the three files, a panel per option with ids `a`, `b` and `c`, `#a`/`#b`/`#c` links labelled with each option's label, styles prefixed by panel id and page-level rules moved onto the panel, the options' links as plain text and their ids dropped, `:target` with A shown by default, and the link in the design's "Sketches" section
- [ ] 1.6 In `bin/check-intentable-result`, make `--sketches` require `compare.html` with the ids `a`, `b` and `c` once each and no other id, and links to `#a`, `#b` and `#c` and no other link, and its link in `design.md`
- [ ] 1.7 Update the install check in `core/tests/test_issue_proposals.py` and add tests for "Wireframe skill pinned", "The sketch prompt asks for wireframes" and "Revise keeps sketches plain", "Comparison page required", "A panel missing from the comparison page", "A comparison page with a stray link", "A comparison page that passes" and "The sketch prompt asks for the comparison page" (adding `compare.html` to the checker tests' safe sketch set); keep "Workflow shape", "Sketch step only for needs-design", "Sketches required with needs-design", "Options for each sketch" and `test_sketch_prompt_rules` passing
- [ ] 1.8 Run `fabro validate` on the workflow and `openspec validate use-html-wireframes --strict`

## 2. Docs

- [ ] 2.1 Update the sketch step in `docs/FABRO.md`

## 3. Merge

- [ ] 3.1 With Nate's G4 and go-ahead to push `main`, merge to the fork's `main`

## 4. Live check

- [ ] 4.1 With Nate's go-ahead, run `spec` for a `needs-design` issue (from the merged `main`, or a test branch through `FABRO_WORKFLOW_REF`)
- [ ] 4.2 Check in the sketch stage's output that the skill was invoked or its `SKILL.md` read; that the three sketches are grayscale, static, differ in structure and reflow at 390px; that `compare.html` switches between them and opens on A, and its panels match the files; that `check_sketches` passed; and that the thumbnails reach the Spek page, timing the `thumbnails` job; tick `add-spec-workflow` 5.3 with the same run
- [ ] 4.3 With Nate's go-ahead to push `main`, archive `add-spec-workflow`, then this change
