## Why

When a proposal needs screens, the `spec` workflow's `sketch` agent runs Impeccable's decision step to make three HTML options. That step was built for picking a finished look: it reaches for the site's colours, type and polish. At G2, though, Nate, Sooz and Mark need to settle what goes on the screen and in what order, not how it looks. Polished sketches invite a review of colours and fonts too early, and Impeccable's mocks tend to pull in web fonts the checker then refuses.

effective-html's `html-wireframe` skill is built for that earlier question: low fidelity, grayscale, system type, real labels and content, two or three structurally different directions. Nate chose it for the sketch step on 7 November 2026 ("Wireframes, Impeccable later"): wireframes at the spec stage, and Impeccable kept for building the design that is picked.

## What Changes

- **The sketch agent makes wireframes.** On the `needs-design` route, `sketch` uses the `html-wireframe` skill instead of Impeccable. It still writes three files, `a.html`, `b.html` and `c.html`, and `options.json` with each option's `file`, `label`, `thesis` and `risk`, and `design.md` still links each one. So the checker, the thumbnails, the Spek pages and the bridge's issue comment don't change.
- **Our rules win over the skill's defaults.** The skill would put the directions in one file with a selector, and add click-through behaviour. The prompt asks for three files, no scripts, no forms and nothing loaded from elsewhere, which the existing checker enforces. Where the skill would use a text field or a select, the sketch draws a labelled box.
- **Grayscale and structural.** The prompt asks for a grayscale palette, system fonts, plain borders and labelled placeholders, no brand colours or images. It asks for options that differ in structure (grouping, order, navigation, where the main action sits), not in colour. Each is laid out at 1440×900, the thumbnail's size, and reflows at 390px wide.
- **The skill is pinned by commit.** effective-html has no release tags. `install` fetches it at a fixed commit and copies only `html-wireframe` into Claude Code's user skills. It doesn't install the plugin, because the repository's marketplace entry points at the unpinned GitHub repository.
- **Impeccable leaves the spec stage.** `install` no longer installs it, and `sketch.md` no longer points at `DESIGN.md` or `.impeccable/`. The sketch reads `PRODUCT.md` and the templates the change touches, for the site's vocabulary and content. The `.impeccable/` files and `DESIGN.md` stay in the repository for the later build stage. Nothing about that stage changes here.
- **`docs/FABRO.md`** says what the sketch step does now.

Out of scope:
- a workflow for building the picked design with Impeccable;
- clickable wireframes (scripts, forms, links between sketches), which would need a change to the checker and to how sketches are published;
- intentable's own docs and diagrams that name Impeccable for this step, which are updated in intentable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `issue-proposals`: the sketch agent uses the pinned `html-wireframe` skill, not Impeccable, and the sketches are low-fidelity wireframes. This capability is still in the unarchived `add-spec-workflow` change, so that change is archived first (see the design).

## Impact

- `.fabro/workflows/spec/workflow.fabro`: the `install` script and the `sketch` step's label.
- `.fabro/workflows/spec/sketch.md`: rewritten for the wireframe skill.
- `core/tests/test_issue_proposals.py`: the install check and the sketch prompt check.
- `docs/FABRO.md`: the sketch step.
- No change to `bin/check-intentable-result`, `bin/publish-spek-page`, `.github/workflows/spek.yml`, the bridge, or the `.impeccable/` files.
- New outside dependency: `plannotator/effective-html` (MIT), fetched at a pinned commit in the sandbox only.
