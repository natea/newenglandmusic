## MODIFIED Requirements

### Requirement: A spec workflow exists

The repo SHALL have a `spec` workflow in `.fabro/workflows/spec/`. It SHALL install Claude Code, its ACP adapter and the `openspec` CLI at pinned versions. Then, in order, it SHALL run:
- an agent that writes the proposal;
- a step that checks the draft;
- a sketch agent, only when a new proposal needs screens, never for a revision;
- three reviewer agents in parallel;
- a step that reads their reports;
- a revise agent, after which the draft is checked and reviewed again;
- a final step that writes the result.

Every check step runs the default branch's copy of its script (see "A revision runs the default branch's checks").

#### Scenario: Workflow shape

- **WHEN** the configuration tests read the `spec` workflow
- **THEN** it installs pinned versions of Claude Code, the ACP adapter and `openspec`. In order, it has:
  - a `propose` agent using `propose.md`;
  - the draft check;
  - the `route` step, which sends a `needs-info` draft straight to the last step, and a revision straight to the fan-out;
  - the `sketch` agent and the `check_sketches` step on the `needs-design` route;
  - a fan-out to the agents `risk`, `spec_fit` and `fidelity`, each using its own prompt;
  - a merge;
  - the review check;
  - a `revise` agent using `revise.md`, which leads back through the draft check to the fan-out;
  - a last step running the default branch's copy, `.intentable/main/check-intentable-result spec`.

#### Scenario: A revision skips the sketch step

- **WHEN** the configuration tests read the graph
- **THEN** the `route` step's unconditional edge reaches the fan-out, and the `sketch` agent is reached only on the `needs-design` route, which the route step never prints for a revision

### Requirement: A proposal that needs screens includes sketches

When a new draft is labelled `needs-design`, a `sketch` agent with the Impeccable skill (pinned) SHALL run once, before the first review, and write three options to `openspec/changes/<change>/sketches/`: `a.html`, `b.html`, `c.html`, and `options.json`, a list with each option's `file`, `label`, `thesis` and `risk`. `design.md` SHALL link each sketch. Otherwise the step SHALL be skipped (Nate's decision, 2 November 2026). One sketch is allowed only for a revision: a revision that narrows to a picked option SHALL keep exactly that one sketch, with its `options.json` entry and its link in `design.md` (Nate's decision, 11 November 2026).

#### Scenario: Sketch step only for needs-design

- **WHEN** the configuration tests read the graph
- **THEN** a `sketch` agent using `sketch.md` is reached from the first draft check only on the route for `needs-design`, leads to the fan-out, and is not on the revise loop

#### Scenario: Sketches required with needs-design

- **WHEN** the draft has the label `needs-design` and `openspec/changes/add-venue-hours/sketches/` lacks `c.html` or `options.json`, or `design.md` doesn't link `sketches/a.html`
- **THEN** `bin/check-intentable-result spec --sketches` exits with a failure naming what is missing

#### Scenario: Options for each sketch

- **WHEN** `options.json` isn't a JSON list, has no entry for `c.html`, or has an empty thesis or risk
- **THEN** `--sketches` exits with a failure naming what is missing, since the issue comment shows them (Nate's decision, 3 November 2026)

#### Scenario: One sketch after a pick

- **WHEN** a revision draft with the label `needs-design` has only `sketches/c.html`, `options.json` with an entry for `c.html`, and `design.md` linking it
- **THEN** the last step's check accepts it

#### Scenario: Two sketches

- **WHEN** a revision draft with `needs-design` has `sketches/a.html` and `sketches/c.html` only, or a new draft has only `sketches/c.html`
- **THEN** the last step exits with a failure saying a new draft has three options and a narrowed revision one

### Requirement: The spec workflow follows the workflow contract

The `spec` workflow SHALL declare the inputs `issue_number`, `issue_title`, `issue_body`, `issue_author`, `issue_thread`, `change_name`, `feedback` and `revision_scope`, each with an empty default, and its propose prompt SHALL use all eight. No command step SHALL contain an input. The graph SHALL set `on_failure="exit"`, have no human gate, use no child workflow, and every `@` file reference SHALL be inside its own folder.

#### Scenario: Inputs used, commands without inputs

- **WHEN** the configuration tests read the `spec` workflow
- **THEN** it declares the eight inputs, `propose.md` refers to every one, and no command step contains `{{ inputs.`

#### Scenario: No gate, no children, references inside

- **WHEN** the configuration tests read the graph
- **THEN** it sets `on_failure="exit"`, has no human gate, names no child workflow, and each `@` reference names a file in `.fabro/workflows/spec/`

### Requirement: The spec result names the change

The last step, the checker's `spec` mode, SHALL write `.intentable/result.json` from `.intentable/draft.json` and `.intentable/reviews/outcome`. For a draft with a change, it SHALL hold `change`, the change's name; `labels`, none or only `needs-design`; `state`, none; `message`, plain text for the person who asked; `reviewed`, `passed` or `not-passed`; and `files`, every file of the change, relative to its folder, dotfiles such as `.openspec.yaml` included. For a revision it SHALL also hold `revision: true`.

#### Scenario: A good result

- **WHEN** the draft names `add-venue-hours`, which validates and is new, with no labels and a two-sentence message, and the review passed
- **THEN** the checker writes a result with that change, no state, the message, `reviewed: passed` and `files` such as `[".openspec.yaml", "design.md", "proposal.md", "specs/venues/spec.md", "tasks.md"]`

#### Scenario: A revision's result

- **WHEN** the draft is a revision of `add-band-discovery-swipe` and the review passed
- **THEN** the result holds that change, `revision: true`, `reviewed: passed` and the folder's files after the revision

### Requirement: The change name is plain and new

`bin/check-intentable-result spec`, with or without `--draft`, SHALL fail the run, naming the problem, when:
- `change` isn't a kebab-case name of lowercase letters, digits and single hyphens, at most 60 characters;
- the change folder is missing;
- the change existed before the run in `openspec/changes/`, or in its archive with any `YYYY-MM-DD-` prefix removed, unless the draft is a revision;
- the draft is a revision, and its change didn't exist in `openspec/changes/` before the run, or another change folder is new.

#### Scenario: A name that isn't plain

- **WHEN** the draft's `change` is `../add-x` or `Add Venue Hours`
- **THEN** the checker exits with a failure about the name

#### Scenario: A change that already existed

- **WHEN** the draft names `add-spek-pages`, archived as `2026-11-02-add-spek-pages`
- **THEN** the checker exits with a failure saying the change already exists

#### Scenario: No change folder

- **WHEN** the draft names `add-venue-hours` and `openspec/changes/add-venue-hours/` doesn't exist
- **THEN** the checker exits with a failure saying the folder is missing

#### Scenario: A revision of an existing change

- **WHEN** the draft is a revision of `add-band-discovery-swipe`, which existed before the run, and no other change folder is new
- **THEN** the checker accepts the name

#### Scenario: A revision that makes a new change

- **WHEN** the draft is a revision of `add-band-discovery-swipe`, and the agent also created `openspec/changes/add-swipe-deck/`
- **THEN** the checker exits with a failure naming `add-swipe-deck` as new

### Requirement: The fidelity reviewer reads the decision record

The fidelity prompt SHALL give as the decision record the issue thread, `AGENTS.md`, and the designs of the archived changes in `openspec/changes/archive/`. For a revision, the fidelity prompt SHALL also say to check each point of the feedback in the change's files, and each question in the message, and to treat a point not acted on, or a question not answered, as blocking, unless the message gives the reason. The fidelity prompt and the propose prompt SHALL both say that a comment ending with `<!-- intentable-bridge -->` is the bridge's, not the owner speaking.

#### Scenario: Decision record and bridge comments

- **WHEN** the configuration tests read `fidelity.md` and `propose.md`
- **THEN** `fidelity.md` names the thread, `AGENTS.md` and `openspec/changes/archive/`, and both say a comment ending with the bridge marker isn't the owner speaking

#### Scenario: Fidelity checks each point of the feedback

- **WHEN** the configuration tests read `fidelity.md`
- **THEN** it says that for a revision each point is checked in the files and each question in the message, and that one left without a reason is blocking

### Requirement: The proposal prompt states the rules

`propose.md` SHALL tell the agent to write planning artifacts only, grounded in the site's code; to follow `openspec/config.yaml` and `AGENTS.md`; to choose a new change name; to keep host and network names out; to record unsettled decisions as open questions; to send the issue back with one question when it isn't clear enough; and to write the message in two to four plain sentences, with no @-mentions. These are the rules for a new draft. A revision follows them except that it keeps its change's name, never sends the issue back, and may use up to six sentences (see "A revision's message answers the feedback").

#### Scenario: The prompt gives the rules

- **WHEN** the configuration tests read `propose.md`
- **THEN** it says:
  - to write planning artifacts only;
  - to follow `openspec/config.yaml` and `AGENTS.md`;
  - to keep host and network names out;
  - to record unsettled decisions as open questions;
  - when to send the issue back with one question;
  - to write the message in two to four sentences without @-mentions;
  - to write `.intentable/draft.json`.

#### Scenario: The prompt gives a revision's exceptions

- **WHEN** the configuration tests read `propose.md`
- **THEN** its revision section says to keep the change's name, not to send the issue back, and to use at most six sentences

### Requirement: Sketches are checked as soon as they are made

A `check_sketches` step SHALL run right after `sketch`, before the fan-out, running `.intentable/main/check-intentable-result spec --sketches`: the sketches are present, linked from `design.md`, and safe to publish. The draft check after revise SHALL check the safety of any sketches again, and the last step SHALL repeat the full `--sketches` check when the recorded labels include `needs-design`. For a new draft, the first draft check, before `sketch`, SHALL NOT require sketches.

#### Scenario: Unsafe sketch caught before review

- **WHEN** the sketch agent writes a `b.html` that loads a stylesheet from another address
- **THEN** `check_sketches` fails the run before any reviewer starts

#### Scenario: A sketch lost in revise

- **WHEN** revise deletes `sketches/c.html` from a `needs-design` change
- **THEN** the last step exits with a failure naming the missing sketch

#### Scenario: First draft check without sketches

- **WHEN** `--draft` runs on a new `needs-design` draft that has no `sketches/` yet
- **THEN** it accepts the draft

## ADDED Requirements

### Requirement: A revision answers the feedback

When `feedback` isn't empty, the propose agent SHALL revise the change `change_name` instead of writing a new one, and SHALL write `.intentable/draft.json` with `revision: true`, that `change` and the draft's labels. It SHALL act on each point of the feedback, changing the specs and their scenarios where the feedback changes behaviour, and record what the feedback leaves undecided as an open question. A revision SHALL NOT send the issue back.

#### Scenario: The propose prompt has the revision section

- **WHEN** the configuration tests read `propose.md`
- **THEN** it contains `{{ inputs.feedback }}` and `{{ inputs.change_name }}`, and says to revise that change rather than write a new one, and to write `revision: true`

#### Scenario: A revision that asks a question back

- **WHEN** a revision draft has the state `needs-info`
- **THEN** `bin/check-intentable-result spec --draft` exits with a failure saying a revision can't send the issue back

### Requirement: A revision after G2 changes only the sketches

When `revision_scope` is `sketches`, the propose agent SHALL change only files under `sketches/` and the design's "Sketches" section, since Nate has confirmed the rest, and SHALL write `"scope": "sketches"` in the draft. Its message SHALL name each request that would need the proposal itself changed.

#### Scenario: The prompt limits a revision after G2

- **WHEN** the configuration tests read `propose.md`
- **THEN** its revision section contains `{{ inputs.revision_scope }}` and says that with `sketches` only the sketches and the "Sketches" section change, and other requests are named in the message

### Requirement: The draft check enforces a sketch-only revision

The draft check SHALL fail a draft with `"scope": "sketches"` that changes anything but files under `sketches/` and the design's "Sketches" section, compared with the commit `install` recorded in `.intentable/base` before any agent ran, since Fabro's checkpoint commits move `HEAD`.

#### Scenario: A sketch-only revision that changes the spec

- **WHEN** a revision draft with `"scope": "sketches"` also changed `specs/band-discovery/spec.md`, and a checkpoint commit after the propose step holds that edit
- **THEN** the draft check exits with a failure naming that file

### Requirement: A revision's message answers the feedback

A revision's message SHALL say what changed, answer each question the feedback asks, and name any request outside the issue's scope as one to file as its own issue (Nate's decision, 11 November 2026). The checker refuses a mention or more than 2,000 characters, as for a new draft, and the prompt asks for at most six plain sentences.

#### Scenario: The prompt asks for answers

- **WHEN** the configuration tests read `propose.md`
- **THEN** its revision section says to answer each question in the message and to name out-of-scope requests as their own issues

### Requirement: A pick with changes narrows to one sketch

When the feedback picks one of the sketches and asks for changes to it, the propose agent SHALL revise that sketch under its own letter, remove the others and their `options.json` entries, and keep `design.md`'s "Sketches" section to that one (Nate's decision, 11 November 2026: "narrow it down to one refined sketch rather than expanding to more variations"). The revise agent SHALL keep a narrowed revision at one sketch.

#### Scenario: Prompts keep one sketch

- **WHEN** the configuration tests read `propose.md` and `revise.md`
- **THEN** `propose.md` says a pick with changes keeps only that sketch, revised, and `revise.md` says not to add sketches back to a revision that has one

### Requirement: A revision runs the default branch's checks

The `install` step SHALL copy `bin/check-intentable-result`, `bin/check-intentable-reviews` and `.fabro/workflows/spec/sketch.md` from the default branch into `.intentable/main/`, and every check step SHALL run those copies. A revision's checkout is its draft branch, which can predate the current checks, as the build's checkout can (`issue-builds`). The propose prompt SHALL point a revision at `.intentable/main/sketch.md` for the sketch rules.

#### Scenario: A revision on a branch cut before this change

- **WHEN** a revision run's checkout is a draft branch whose `bin/check-intentable-result` has no revision rules
- **THEN** the draft check that runs is the default branch's, and it accepts the revision

#### Scenario: Check steps run the copies

- **WHEN** the configuration tests read the graph
- **THEN** `install` fetches the default branch and copies the three files into `.intentable/main/`, and every check step runs `python3 .intentable/main/check-intentable-…`

### Requirement: A revision's draft is checked like a new one

`bin/check-intentable-result spec --draft` SHALL check a revision with every rule a new draft has, except that its change existed before the run. For a revision labelled `needs-design` it SHALL also require the sketch set (three, or one), since a revision doesn't pass the `--sketches` step. The route step SHALL record the revision's labels and change, as for a new draft, and send it to review, so the sketch agent doesn't run.

#### Scenario: A revision goes straight to review

- **WHEN** the route step reads a revision draft with the label `needs-design`
- **THEN** it records the labels and change and prints the route `revised`, and the sketch agent doesn't run

#### Scenario: Two sketches at the first check

- **WHEN** a revision draft with `needs-design` has only `sketches/a.html` and `sketches/c.html`
- **THEN** the draft check exits with a failure, before any review

#### Scenario: An unsafe sketch in a revision

- **WHEN** a revision's `sketches/c.html` has a script
- **THEN** the draft check exits with a failure naming `sketches/c.html`
