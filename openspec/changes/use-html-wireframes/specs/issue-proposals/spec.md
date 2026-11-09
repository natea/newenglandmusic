## MODIFIED Requirements

### Requirement: A proposal that needs screens includes sketches

When the draft is labelled `needs-design`, a `sketch` agent with effective-html's `html-wireframe` skill (pinned) SHALL run once, before the first review, and write three options to `openspec/changes/<change>/sketches/`: `a.html`, `b.html`, `c.html`, and `options.json`, a list with each option's `file`, `label`, `thesis` and `risk`. `design.md` SHALL link each sketch. Otherwise the step SHALL be skipped (Nate's decisions, 2 and 7 November 2026).

#### Scenario: Sketch step only for needs-design

- **WHEN** the configuration tests read the graph
- **THEN** a `sketch` agent using `sketch.md` is reached from the first draft check only on the route for `needs-design`, leads to the fan-out, and is not on the revise loop

#### Scenario: Sketches required with needs-design

- **WHEN** the draft has the label `needs-design` and `openspec/changes/add-venue-hours/sketches/` lacks `c.html` or `options.json`, or `design.md` doesn't link `sketches/a.html`
- **THEN** `bin/check-intentable-result spec --sketches` exits with a failure naming what is missing

#### Scenario: Options for each sketch

- **WHEN** `options.json` isn't a JSON list, has no entry for `c.html`, or has an empty thesis or risk
- **THEN** `--sketches` exits with a failure naming what is missing, since the issue comment shows them (Nate's decision, 3 November 2026)

## ADDED Requirements

### Requirement: Sketches are low-fidelity wireframes

The `spec` workflow SHALL install the `html-wireframe` skill from effective-html at a fixed commit, and SHALL NOT install Impeccable. `sketch.md` SHALL name the skill and ask for three structurally different static options in three files: grayscale, system fonts, labelled placeholders, no scripts and no forms, laid out at 1440×900 and reflowing at 390px. `revise.md` SHALL keep edited sketches grayscale (Nate's decision, 7 November 2026, as worked out in this change's design).

#### Scenario: Wireframe skill pinned

- **WHEN** the configuration tests read the `install` step
- **THEN** it fetches `plannotator/effective-html` at a full 40-character commit and copies `skills/html-wireframe` into Claude Code's user skills, and it installs no Impeccable plugin

#### Scenario: The sketch prompt asks for wireframes

- **WHEN** the configuration tests read `sketch.md`
- **THEN** it names `html-wireframe`; asks for three files `a.html`, `b.html` and `c.html` rather than one file with a selector; says grayscale, labelled placeholders, 1440×900 and 390px; says no scripts and no forms; names the refused `label for=`; and doesn't name `DESIGN.md`, `.impeccable/design.json` or `.impeccable/mocks/`

#### Scenario: Revise keeps sketches plain

- **WHEN** the configuration tests read `revise.md`
- **THEN** it says an edited sketch stays a grayscale wireframe

### Requirement: A comparison page switches between the sketches

With the three sketches, the `sketch` agent SHALL write `sketches/compare.html`: a panel for each option with the ids `a`, `b` and `c`, switched by `#a`, `#b` and `#c` links with CSS `:target` and no script, showing `a` when nothing is targeted. `--sketches` SHALL require it, its three panels and links, and a link to it from `design.md`, and SHALL check its safety like any sketch (Nate's choice, 9 November 2026).

#### Scenario: Comparison page required

- **WHEN** a `needs-design` change has `a.html`, `b.html`, `c.html` and `options.json` but no `sketches/compare.html`, or `design.md` doesn't link `sketches/compare.html`
- **THEN** `--sketches` exits with a failure naming what is missing

#### Scenario: A panel missing from the comparison page

- **WHEN** `compare.html` has no element with the id `c`, or no link to `#c`
- **THEN** `--sketches` exits with a failure naming `compare.html` and `c`

#### Scenario: A comparison page that passes

- **WHEN** `compare.html` has the three panels and links, inline styles using `:target` and `:has`, and nothing else the allowlist refuses
- **THEN** `--sketches` accepts it

#### Scenario: The sketch prompt asks for the comparison page

- **WHEN** the configuration tests read `sketch.md` and `revise.md`
- **THEN** `sketch.md` asks for `compare.html` with `:target` panels `a`, `b` and `c`, written after the three files, and `revise.md` says to keep `compare.html` in step with an edited sketch
