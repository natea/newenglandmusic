## ADDED Requirements

### Requirement: A spec workflow exists

The repo SHALL have a `spec` workflow in `.fabro/workflows/spec/`. It SHALL install Claude Code, its ACP adapter and the `openspec` CLI at pinned versions. Then, in order, it SHALL run:
- an agent that writes the proposal;
- a step that checks the draft;
- three reviewer agents in parallel;
- a step that reads their reports;
- a revise agent, after which the draft is checked and reviewed again;
- a final step that writes the result.

#### Scenario: Workflow shape

- **WHEN** the configuration tests read the `spec` workflow
- **THEN** it installs pinned versions of Claude Code, the ACP adapter and `openspec`. In order, it has:
  - a `propose` agent using `propose.md`;
  - the draft check;
  - a fan-out to the agents `risk`, `spec_fit` and `fidelity`, each using its own prompt;
  - a merge;
  - the review check;
  - a `revise` agent using `revise.md`, which leads back through the draft check to the fan-out;
  - a last step running `bin/check-intentable-result spec`.

### Requirement: Every agent runs through ACP

Every agent step of the `spec` workflow SHALL be Claude Code through ACP (`backend="acp"`), so it runs on the Max subscription like `triage` and `clarify`.

#### Scenario: Every agent through ACP

- **WHEN** the configuration tests read every agent step of the graph
- **THEN** each has `backend="acp"` and the `claude-agent-acp` command, and no step is a prompt stage that calls a model directly

### Requirement: The spec workflow follows the workflow contract

The `spec` workflow SHALL declare the inputs `issue_number`, `issue_title`, `issue_body`, `issue_author` and `issue_thread`, and its propose prompt SHALL use all five. No command step SHALL contain an input. The graph SHALL set `on_failure="exit"`, have no human gate, use no child workflow, and every `@` file reference SHALL be inside its own folder.

#### Scenario: Inputs used, commands without inputs

- **WHEN** the configuration tests read the `spec` workflow
- **THEN** it declares the five inputs, `propose.md` refers to every one, and no command step contains `{{ inputs.`

#### Scenario: No gate, no children, references inside

- **WHEN** the configuration tests read the graph
- **THEN** it sets `on_failure="exit"`, has no human gate, names no child workflow, and each `@` reference names a file in `.fabro/workflows/spec/`

### Requirement: The spec workflow pushes nothing

The `spec` workflow SHALL NOT push a run branch or open a pull request, and SHALL ask Fabro for no GitHub permissions. The finished change SHALL leave the sandbox only as run artifacts.

#### Scenario: Nothing pushed

- **WHEN** the configuration tests read the workflow's settings
- **THEN** it disables pull requests and run-branch pushing, declares no GitHub integration permissions, and collects exactly `.intentable/result.json`, `.intentable/review.md` and `.intentable/proposal/**`

### Requirement: Reviewers are fresh, one lens each

Each reviewer SHALL be its own agent step with its own prompt and one lens: risk, spec fit or fidelity. Each prompt SHALL word its lens as the `dev-review-proposal` skill does. Spec fit's design rules SHALL be `openspec/config.yaml` and `AGENTS.md`. Fidelity SHALL treat a decision taken without the requester or the owner, and left unflagged, as blocking.

#### Scenario: Three lenses

- **WHEN** the configuration tests read the three reviewer prompts
- **THEN** each names one of the lenses risk, spec fit and fidelity, and no two name the same. The risk prompt asks for readers the task list misses. The spec fit prompt names `openspec/config.yaml` and `AGENTS.md` as the design rules. The fidelity prompt says an unflagged decision is blocking.

### Requirement: The fidelity reviewer reads the decision record

The fidelity prompt SHALL give as the decision record the issue thread, `AGENTS.md`, and the designs of the archived changes in `openspec/changes/archive/`. The fidelity prompt and the propose prompt SHALL both say that a comment ending with `<!-- intentable-bridge -->` is the bridge's, not the owner speaking.

#### Scenario: Decision record and bridge comments

- **WHEN** the configuration tests read `fidelity.md` and `propose.md`
- **THEN** `fidelity.md` names the thread, `AGENTS.md` and `openspec/changes/archive/`, and both say a comment ending with the bridge marker isn't the owner speaking

### Requirement: Reviewers write reports and edit nothing

Each reviewer SHALL write its report to `.intentable/reviews/<lens>.md` in the `dev-review-proposal` format: `SATISFIED: yes` or `SATISFIED: no`, then `BLOCKING:`, `NON-BLOCKING:` and `CONFIRMED OK:`, with `none` under an empty heading. It SHALL be told to change no other file. From the second round on, it SHALL be given the revise notes of the round before, as what changed since the last read.

#### Scenario: Reviewer prompts

- **WHEN** the configuration tests read the three reviewer prompts
- **THEN** each names its own report file, gives the four headings and the `none` rule, tells the reviewer to edit nothing else, and refers to the previous round's revise notes

### Requirement: Revise records what it did

The revise agent SHALL apply every blocking finding, and the non-blocking ones it agrees with. It SHALL write `.intentable/reviews/revise.md` listing each finding with how it was fixed, or why it wasn't applied. It SHALL NOT rename the change, and SHALL write nothing under `.intentable/proposal/`.

#### Scenario: Revise prompt

- **WHEN** the configuration tests read `revise.md`
- **THEN** it says to apply every blocking finding, to write each finding with its fix or reason to `.intentable/reviews/revise.md`, and not to rename the change

### Requirement: The review loop ends

`bin/check-intentable-reviews` SHALL keep each round's three reports under `.intentable/reviews/<round>/`, and the revise notes written after round N under `.intentable/reviews/<N>/` with that round's reports. It SHALL end the loop when all three reports start `SATISFIED: yes`. It SHALL send the draft to revise when any says no, unless three rounds have run. After the third round it SHALL end the loop with the review not passed. A missing or unreadable report SHALL count as not satisfied.

#### Scenario: All satisfied

- **WHEN** the three reports of round 1 each start `SATISFIED: yes`
- **THEN** the check ends the loop with the review passed after 1 round

#### Scenario: One not satisfied

- **WHEN** the risk report of round 1 starts `SATISFIED: no` and the others say yes
- **THEN** the check sends the draft to revise

#### Scenario: The round limit

- **WHEN** a report of round 3 still says no
- **THEN** the check ends the loop with the review not passed after 3 rounds

#### Scenario: Missing report

- **WHEN** the fidelity report is missing
- **THEN** the check counts it as not satisfied

### Requirement: The review is summed up for Nate

When the loop ends, `bin/check-intentable-reviews` SHALL write `.intentable/reviews/outcome`, `passed` or `not-passed`, and the review summary, `.intentable/reviews/summary.md`. The summary's first line SHALL be exactly `Passed by the reviewers after <n> round(s).` or `Not passed by the reviewers after <n> rounds.`, followed by every round's blocking findings and the revise notes filed with them.

#### Scenario: Summary written

- **WHEN** a run's review ends after 2 rounds with all three satisfied
- **THEN** `.intentable/reviews/summary.md` starts with the line `Passed by the reviewers after 2 round(s).` and holds round 1's blocking findings and the revise notes filed with them, and `.intentable/reviews/outcome` is `passed`

#### Scenario: Summary of a review not passed

- **WHEN** the review ends at the round limit
- **THEN** `.intentable/reviews/summary.md` starts with the line `Not passed by the reviewers after 3 rounds.`, and `.intentable/reviews/outcome` is `not-passed`

### Requirement: The summary is collected with the result

The last step SHALL copy `.intentable/reviews/summary.md` to `.intentable/review.md`, so it is collected in the same stage as the result.

#### Scenario: Summary beside the result

- **WHEN** the last step accepts a draft
- **THEN** `.intentable/review.md` is the same text as `.intentable/reviews/summary.md`, and no earlier step wrote `.intentable/review.md`

### Requirement: The draft is named in its own file

The propose agent SHALL name the change and give its message in `.intentable/draft.json`, as `change`, `labels` and `message`. The revise agent may change the message and labels, but not the change name. No step before the last SHALL write `.intentable/result.json`, `.intentable/review.md` or anything under `.intentable/proposal/`.

#### Scenario: Draft check reads the draft file

- **WHEN** `bin/check-intentable-result spec --draft` runs with `.intentable/draft.json` naming a valid new change
- **THEN** it accepts the draft and writes neither `.intentable/result.json` nor `.intentable/proposal/`

### Requirement: The spec result names the change

The last step, `bin/check-intentable-result spec`, SHALL write `.intentable/result.json` from `.intentable/draft.json` and `.intentable/reviews/outcome`. It SHALL hold `change`, the change's name; `labels`, none or only `needs-design`; `state`, none; `message`, plain text for the person who asked; `reviewed`, `passed` or `not-passed`; and `files`, every path copied, relative to the change folder, dotfiles such as `.openspec.yaml` included.

#### Scenario: A good result

- **WHEN** the draft names `add-venue-hours`, which validates and is new, with no labels and a two-sentence message, and the review passed
- **THEN** the checker writes a result with that change, no state, the message, `reviewed: passed` and `files` such as `[".openspec.yaml", "design.md", "proposal.md", "specs/venues/spec.md", "tasks.md"]`

### Requirement: The proposal is copied last

The last step SHALL empty `.intentable/proposal/`, then copy the contents of `openspec/changes/<change>/` into it, so `.intentable/proposal/proposal.md` is the change's `proposal.md`.

#### Scenario: Only the final text

- **WHEN** `.intentable/proposal/` holds a stale `notes.md` and the checker accepts `add-venue-hours`
- **THEN** `.intentable/proposal/` holds exactly the contents of `openspec/changes/add-venue-hours/`, without `notes.md`

### Requirement: The change name is plain and new

`bin/check-intentable-result spec`, with or without `--draft`, SHALL fail the run, naming the problem, when:
- `change` isn't a kebab-case name of lowercase letters, digits and single hyphens, at most 60 characters;
- the change folder is missing;
- the change existed before the run in `openspec/changes/`, or in its archive with any `YYYY-MM-DD-` prefix removed.

#### Scenario: A name that isn't plain

- **WHEN** the draft's `change` is `../add-x` or `Add Venue Hours`
- **THEN** the checker exits with a failure about the name, and copies nothing

#### Scenario: A change that already existed

- **WHEN** the draft names `add-spek-pages`, archived as `2026-11-02-add-spek-pages`
- **THEN** the checker exits with a failure saying the change already exists

#### Scenario: No change folder

- **WHEN** the draft names `add-venue-hours` and `openspec/changes/add-venue-hours/` doesn't exist
- **THEN** the checker exits with a failure saying the folder is missing

### Requirement: Spec drafts must be valid and collectable

`bin/check-intentable-result spec`, with or without `--draft`, SHALL also fail the run, naming the problem, when:
- the change doesn't pass `openspec validate <change> --strict`;
- the change has more than 90 files;
- the change has a file that isn't UTF-8 text;
- the change has a path segment that Fabro skips when collecting: `.git`, `node_modules`, `target`, `dist`, `.venv` or `.cache`.

#### Scenario: Too many files

- **WHEN** the named change holds 91 files
- **THEN** the checker exits with a failure giving the count and the cap

#### Scenario: A file Fabro wouldn't collect

- **WHEN** the change has `specs/dist/spec.md` or a binary image
- **THEN** the checker exits with a failure naming the file

#### Scenario: Invalid change

- **WHEN** `openspec validate` fails for the named change
- **THEN** the checker exits with a failure that includes the validator's summary line

### Requirement: Spec drafts give no state and follow the message rules

`bin/check-intentable-result spec`, with or without `--draft`, SHALL fail the run, naming the problem, when the draft has a `state` key with any value other than none, or a label other than `needs-design`, or when its message is missing, mentions anyone, or is longer than the other workflows allow.

#### Scenario: A state or another label

- **WHEN** the draft gives the state `building` or the label `ai-shippable`
- **THEN** the checker exits with a failure naming it

#### Scenario: A message that mentions someone

- **WHEN** the draft's message mentions `@sooz`
- **THEN** the checker exits with a failure saying messages mention no one

### Requirement: The proposal prompt states the rules

`propose.md` SHALL tell the agent to:
- take the OpenSpec propose stance, writing planning artifacts only and no code;
- ground the change in the site's code;
- follow `openspec/config.yaml` and `AGENTS.md`;
- choose a new change name;
- keep host and network names out of OpenSpec files;
- record any decision the thread doesn't settle as an open question, never as settled;
- write the message in two to four plain sentences, with no @-mentions.

#### Scenario: The prompt gives the rules

- **WHEN** the configuration tests read `propose.md`
- **THEN** it says:
  - to write planning artifacts only;
  - to follow `openspec/config.yaml` and `AGENTS.md`;
  - to keep host and network names out;
  - to record unsettled decisions as open questions;
  - to write the message in two to four sentences without @-mentions;
  - to write `.intentable/draft.json`.

### Requirement: A guide explains the spec workflow

`docs/FABRO.md` SHALL describe the `spec` workflow: when the bridge starts it, the review loop and its limit, what the run leaves, and that the bridge, not the run, pushes the draft.

#### Scenario: Guide

- **WHEN** the tests read `docs/FABRO.md`
- **THEN** it has a section on the `spec` workflow that names `.intentable/proposal/`, the three lenses and the three-round limit
