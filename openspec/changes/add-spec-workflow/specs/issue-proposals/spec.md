## ADDED Requirements

### Requirement: A spec workflow exists

The repo SHALL have a `spec` workflow in `.fabro/workflows/spec/`. It SHALL install Claude Code, its ACP adapter and the `openspec` CLI at pinned versions. Then, in order, it SHALL run:
- an ACP agent that writes the proposal;
- a step that checks the draft;
- three reviewer agents in parallel;
- a step that reads their reports;
- a revise agent, after which the reviewers run again;
- a final check of the result.

#### Scenario: Workflow shape

- **WHEN** the configuration tests read the `spec` workflow
- **THEN** it installs pinned versions of Claude Code, the ACP adapter and `openspec`, and has a propose agent using `propose.md`, a fan-out to the agents `risk`, `spec_fit` and `fidelity` using their own prompts, a merge, the review check, a `revise` agent using `revise.md` that leads back, through the draft check, to the fan-out, and a last step running `bin/check-intentable-result spec`

### Requirement: The spec workflow follows the workflow contract

The `spec` workflow SHALL declare the inputs `issue_number`, `issue_title`, `issue_body`, `issue_author` and `issue_thread`, and its propose prompt SHALL use all five. No command step SHALL contain an input. The graph SHALL set `on_failure="exit"`, have no human gate, use no child workflow, and refer only to files inside its own folder.

#### Scenario: Inputs used, commands without inputs

- **WHEN** the configuration tests read the `spec` workflow
- **THEN** it declares the five inputs, `propose.md` refers to every one, and no command step contains `{{ inputs.`

#### Scenario: No gate, no children

- **WHEN** the configuration tests read the graph
- **THEN** it sets `on_failure="exit"`, has no human gate, and names no child workflow

### Requirement: The spec workflow pushes nothing

The `spec` workflow SHALL NOT push a run branch or open a pull request, and SHALL ask Fabro for no GitHub permissions. The finished change SHALL leave the sandbox only as run artifacts.

#### Scenario: Nothing pushed

- **WHEN** the configuration tests read the workflow's settings
- **THEN** it disables pull requests and run-branch pushing, declares no GitHub integration permissions, and collects exactly `.intentable/result.json`, `.intentable/review.md` and `.intentable/proposal/**`

### Requirement: Reviewers are fresh, one lens each

Each reviewer SHALL be its own agent step with its own prompt and one lens:
- risk: the change traced against the real code and data;
- spec fit: delta format, scenarios kept, vocabulary, testable scenarios, artifacts agreeing with one another;
- fidelity: what the person who asked said in the thread, and the repository's recorded rules, honored or named as violated.

#### Scenario: Three lenses

- **WHEN** the configuration tests read the three reviewer prompts
- **THEN** each names one of the lenses risk, spec fit and fidelity, and no two name the same

### Requirement: Reviewers write reports and edit nothing

Each reviewer SHALL write its report, in the `dev-review-proposal` format starting `SATISFIED: yes` or `SATISFIED: no`, to `.intentable/reviews/<lens>.md`, and SHALL be told to change no other file.

#### Scenario: Reviewer prompts

- **WHEN** the configuration tests read the three reviewer prompts
- **THEN** each names its own lens and its own report file, gives the report format with `SATISFIED:`, `BLOCKING:`, `NON-BLOCKING:` and `CONFIRMED OK:`, and tells the reviewer to edit nothing else

### Requirement: The review loop ends

`bin/check-intentable-reviews` SHALL read the three reports for the current round. It SHALL end the loop when all three start `SATISFIED: yes`. It SHALL send the draft to revise when any says no, unless three rounds have run. After the third round it SHALL end the loop with the review marked as not passed. A missing or unreadable report SHALL count as not satisfied.

#### Scenario: All satisfied

- **WHEN** the three reports of round 1 each start `SATISFIED: yes`
- **THEN** the check ends the loop with the review passed after 1 round

#### Scenario: One not satisfied

- **WHEN** the risk report of round 1 starts `SATISFIED: no` and the others say yes
- **THEN** the check sends the draft to revise

#### Scenario: The round limit

- **WHEN** a report of round 3 still says no
- **THEN** the check ends the loop with the review marked not passed after 3 rounds

#### Scenario: Missing report

- **WHEN** the fidelity report is missing
- **THEN** the check counts it as not satisfied

### Requirement: The review is summed up for Nate

The revise agent SHALL record, for each finding it doesn't apply, the finding and the reason. At the end of the loop, `.intentable/review.md` SHALL say:
- whether the reviewers passed the draft, and after how many rounds;
- the blocking findings and how each was fixed;
- the findings not applied, with their reasons;
- the open questions for Nate.

#### Scenario: Summary written

- **WHEN** a run's review ends, passed or not
- **THEN** `.intentable/review.md` exists and says whether it passed and after how many rounds

### Requirement: The spec result names the change

The spec workflow's `.intentable/result.json` SHALL hold:
- `change`: the change's name;
- `labels`: none, or only `needs-design`, when the proposal needs screens;
- `state`: none;
- `message`: two to four plain sentences for the person who asked, saying what the proposal covers.

#### Scenario: A good result

- **WHEN** the result names `add-venue-hours`, which validates and is new, with no state and a two-sentence message
- **THEN** the checker accepts it and copies `openspec/changes/add-venue-hours/` to `.intentable/proposal/`

### Requirement: The change name is plain and new

`bin/check-intentable-result spec` SHALL fail the run, naming the problem, when `change` isn't a kebab-case name of lowercase letters, digits and single hyphens, at most 60 characters; when the change folder is missing; or when the change existed in `openspec/changes/` or its archive before the run.

#### Scenario: A name that isn't plain

- **WHEN** the result's `change` is `../add-x` or `Add Venue Hours`
- **THEN** the checker exits with a failure about the name, and copies nothing

#### Scenario: A change that already existed

- **WHEN** the result names `add-spek-pages`, already in the archive
- **THEN** the checker exits with a failure saying the change already exists

### Requirement: Spec results must be valid and within bounds

`bin/check-intentable-result spec` SHALL also fail the run, naming the problem, when:
- the change doesn't pass `openspec validate <change> --strict`;
- the change has more than 90 files;
- the result names a state, or a label other than `needs-design`;
- the message breaks the message rules the other workflows follow.

#### Scenario: A state or another label

- **WHEN** the result gives the state `building` or the label `ai-shippable`
- **THEN** the checker exits with a failure naming it

#### Scenario: Too many files

- **WHEN** the named change holds 91 files
- **THEN** the checker exits with a failure giving the count and the cap

#### Scenario: Invalid change

- **WHEN** `openspec validate` fails for the named change
- **THEN** the checker exits with a failure that includes the validator's summary line

### Requirement: The proposal prompt states the rules

`propose.md` SHALL tell the agent to:
- take the OpenSpec propose stance, writing planning artifacts only and no code;
- ground the change in the site's code;
- follow `openspec/config.yaml` and `AGENTS.md`;
- choose a new change name;
- keep host and network names out of OpenSpec files;
- record any decision the thread doesn't settle as an open question, never as settled;
- write the result's message in plain words, with no @-mentions.

#### Scenario: The prompt gives the rules

- **WHEN** the configuration tests read `propose.md`
- **THEN** it says to write planning artifacts only, to follow `openspec/config.yaml` and `AGENTS.md`, to keep host and network names out, to record unsettled decisions as open questions, and to write the message without @-mentions

### Requirement: A guide explains the spec workflow

`docs/FABRO.md` SHALL describe the `spec` workflow: when the bridge starts it, the review loop and its limit, what the run leaves, and that the bridge, not the run, pushes the draft.

#### Scenario: Guide

- **WHEN** the tests read `docs/FABRO.md`
- **THEN** it has a section on the `spec` workflow that names `.intentable/proposal/`, the three lenses and the three-round limit
