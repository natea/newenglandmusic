## Why

When a proposal needs screens, the `spec` workflow's `sketch` agent runs Impeccable's decision step to make three HTML options. That step was built for picking a finished look: it reaches for the site's colours, type and polish. At this stage, though, the question is what goes on the screen and in what order, not how it looks: Nate sees the sketches at G2, and Sooz or Mark pick one later. Polished sketches invite a review of colours and fonts too early, and Impeccable's mocks tend to pull in web fonts the checker then refuses.

effective-html's `html-wireframe` skill is built for that earlier question: low fidelity, grayscale, system type, real labels and content, two or three structurally different directions. Nate chose it for the sketch step on 7 November 2026 ("Wireframes, Impeccable later"): wireframes at the spec stage, and Impeccable kept for building the design that is picked.

## What Changes

- **The sketch agent makes wireframes.** On the `needs-design` route, `sketch` uses the `html-wireframe` skill instead of Impeccable. It still writes three files, `a.html`, `b.html` and `c.html`, and `options.json` with each option's `file`, `label`, `thesis` and `risk`, and `design.md` still links each one. So the thumbnail job's code, the Spek pages and the bridge's issue comment don't change, and the checker only gains the comparison page below (which gets a thumbnail of its own).
- **Our rules win over the skill's defaults.** The skill would put the directions in one file with a selector, and add click-through behaviour. The prompt asks for three static files, because the thumbnails, the bridge's comment (one thumbnail per file, and a reply of a, b or c) and the checker all work per file; the design gives the alternatives. It also keeps the checker's rules (no scripts, no forms, nothing loaded from elsewhere) and lists the elements and attributes the checker allows, since one refused tag fails the run. Where the skill would use a text field or a select, the sketch draws a labelled box.
- **A comparison page too** (Nate's choice, 9 November 2026). Beside the three files, the agent writes `sketches/compare.html`: the three options as panels on one page, switched by `#a`, `#b` and `#c` links with CSS `:target`, no script, opening on A. Links inside the panels become plain text, so only those three links switch anything. The checker requires it, its three panels and those links and no others, `design.md` links it, and it is published and thumbnailed like the others. The bridge's comment doesn't link it yet; that's a later change in intentable.
- **Grayscale and structural.** The prompt asks for a grayscale palette, system fonts, plain borders and labelled placeholders, no brand colours or images. It asks for options that differ in structure (grouping, order, navigation, where the main action sits), not in colour. Each is laid out at 1440×900, the thumbnail's size, and reflows at 390px wide, with a viewport `<meta>` so it does on a phone.
- **The skill is pinned by commit.** effective-html has no release tags. `install` fetches it at a fixed commit and copies only `html-wireframe` into Claude Code's user skills. It doesn't install the plugin, because the repository's marketplace entry points at the unpinned GitHub repository.
- **Impeccable leaves the spec stage.** `install` no longer installs it, and `sketch.md` no longer points at the visual system (`DESIGN.md`, `.impeccable/design.json`, `.impeccable/mocks/`, and the direction contracts in `.impeccable/surfaces/`). The sketch reads `PRODUCT.md`, the "Audience, job and content" sections of `.impeccable/surfaces/`, and the templates the change touches, for the site's audience, vocabulary and content. All those files stay in the repository for the later build stage. Nothing about that stage changes here.
- **Revise keeps the wireframes plain.** `revise.md` says a sketch it edits stays a grayscale wireframe, so a finding about colour or brand doesn't put the visual system back.
- **`docs/FABRO.md`** says what the sketch step does now.

Out of scope:
- a workflow for building the picked design with Impeccable;
- clickable sketches, which stay Nate's open question from `add-spec-workflow` (CSS-only `:target` panels would pass today's checker; scripts would not);
- a link to the comparison page in the bridge's issue comment, which is intentable's;
- intentable's own docs and diagrams that name Impeccable for this step, which are updated in intentable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `issue-proposals`: the sketch agent uses the pinned `html-wireframe` skill, not Impeccable, and the sketches are low-fidelity wireframes. This capability is still in the unarchived `add-spec-workflow` change, so that change is archived first (see the design).

## Impact

- `.fabro/workflows/spec/workflow.fabro`: the `install` script and the `sketch` step's label.
- `.fabro/workflows/spec/sketch.md`: rewritten for the wireframe skill.
- `.fabro/workflows/spec/revise.md`: one line on editing sketches and keeping `compare.html` in step.
- `core/tests/test_issue_proposals.py`: the install check, the sketch prompt check and the comparison page check.
- `docs/FABRO.md`: the sketch step.
- `bin/check-intentable-result`: `--sketches` requires `compare.html` with its panels and links, and its link in `design.md`.
- No change to `bin/publish-spek-page`, `.github/workflows/spek.yml`, the bridge, or the `.impeccable/` files.
- New outside dependency: `plannotator/effective-html` (MIT), fetched at a pinned commit in the sandbox only.
