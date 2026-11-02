## Purpose

Sort and clarify the requests and bug reports that the people on the intentable bridge's intake list open as issues on natea/newenglandmusic, through Fabro workflows the bridge starts in the `daytona` environment: give each issue first-guess labels, ask one question at a time until it is clear enough to write up, and leave a result the bridge applies to the issue.

## ADDED Requirements

### Requirement: Triage and clarify workflows exist

The repo SHALL have a `triage` and a `clarify` workflow in `.fabro/workflows/`. Each SHALL install Claude Code at pinned versions, then run it as an ACP agent with the workflow's prompt, then check the result.

#### Scenario: Workflow shape

- **WHEN** the configuration tests read the `triage` and `clarify` workflows
- **THEN** each runs, in order, an install step with pinned Claude Code and ACP adapter versions, an ACP agent step whose prompt is the workflow's `prompt.md`, and a step that runs `bin/check-intentable-result` with the workflow's name

### Requirement: The workflows take the issue as inputs

Both workflows SHALL declare the inputs `issue_number`, `issue_title`, `issue_body`, `issue_author` and `issue_thread`, and their prompts SHALL use all five.

#### Scenario: Inputs declared and used

- **WHEN** the configuration tests read the two workflows
- **THEN** each declares the five inputs, and each prompt refers to every one of them

### Requirement: Issue text never reaches a command

No command step of either workflow SHALL contain an input, so issue text can't run as a shell command in the sandbox.

#### Scenario: Commands without inputs

- **WHEN** the configuration tests read every command step of the two workflows
- **THEN** none contains `{{ inputs.`

### Requirement: The workflows read the code and push nothing

Both workflows SHALL run against the repository's code, SHALL NOT push a run branch or open a pull request, and SHALL ask Fabro for no GitHub permissions, which would replace the sandbox's read-only git access.

#### Scenario: Nothing pushed

- **WHEN** the configuration tests read the two workflows' settings
- **THEN** both disable pull requests and run-branch pushing, and neither declares any GitHub integration permissions

### Requirement: A run ends with its result

Neither workflow SHALL wait for a person: a question for the person who asked is the run's result. A failed step SHALL end the run as failed.

#### Scenario: No human gate

- **WHEN** the configuration tests read the two graphs
- **THEN** neither has a human gate step, and both set `on_failure="exit"`

### Requirement: The result is kept for the bridge

Each workflow SHALL leave its result in `.intentable/result.json`, collected as a run artifact, and `.intentable/` SHALL be kept out of git.

#### Scenario: Result collected, not committed

- **WHEN** the configuration tests read the two workflows' settings and `.gitignore`
- **THEN** both collect `.intentable/result.json`, and `.gitignore` lists `.intentable/`

### Requirement: Results the bridge would refuse fail the run

`bin/check-intentable-result` SHALL exit with a failure, naming the problem, when the result file is missing or isn't a JSON object of `labels`, `state` and `message`, or names a label outside the bridge's issue labels, a state label, or a state that isn't one.

#### Scenario: No result file

- **WHEN** the checker runs and there is no `.intentable/result.json`
- **THEN** it exits with a failure that says the result is missing

#### Scenario: A label the bridge doesn't know

- **WHEN** a result's labels include `type:question` or `state:building`
- **THEN** the checker exits with a failure naming that label

#### Scenario: Not JSON

- **WHEN** the result file holds `labels: type:bug`
- **THEN** the checker exits with a failure saying the result isn't JSON

### Requirement: Labels for later stages are refused

A result from either workflow SHALL hold no priority label (`P1` to `P5`), no `needs-design` and no `ai-shippable`; those are for later stages to set.

#### Scenario: A label for a later stage

- **WHEN** an otherwise complete result includes `ai-shippable`, `needs-design` or `P2`
- **THEN** the checker exits with a failure naming that label

### Requirement: Triage gives first-guess labels

A triage result SHALL hold exactly one label each of type, clarity, risk, blast radius and size, and SHALL move the issue to `spec-review`, `needs-info` or `parked`, with a message.

#### Scenario: A complete triage result

- **WHEN** a triage result has `type:feature`, `clarity:2`, `risk:2`, `blast:2` and `size:M`, the state `needs-info`, and the message "Should the venue page show past shows as well as upcoming ones?"
- **THEN** the checker accepts it

#### Scenario: A triage result missing a group

- **WHEN** a triage result has no `size:` label
- **THEN** the checker exits with a failure naming size

#### Scenario: Two labels of one group

- **WHEN** a triage result has both `type:bug` and `type:feature`
- **THEN** the checker exits with a failure naming type

### Requirement: Clarify judges clarity afresh

A clarify result SHALL hold exactly one clarity label and at most one label each of type, risk, blast radius and size, and SHALL move the issue to `spec-review` or `needs-info`, with a message.

#### Scenario: Clarify asks again

- **WHEN** a clarify result has `clarity:3`, the state `needs-info`, and the message "Should artists see the venue's booking email, or a contact form?"
- **THEN** the checker accepts it

#### Scenario: Clarify can't park

- **WHEN** a clarify result has the state `parked`
- **THEN** the checker exits with a failure naming the state

### Requirement: Clarity decides the next step

A result SHALL move the issue to `spec-review` exactly when its clarity is 4 or 5, and to `needs-info` exactly when its clarity is 1 to 3. A `parked` triage may have any clarity.

#### Scenario: Unclear but written up

- **WHEN** an otherwise complete result has `clarity:3` and the state `spec-review`
- **THEN** the checker exits with a failure saying clarity 3 needs a question

#### Scenario: Clear but asking

- **WHEN** an otherwise complete result has `clarity:4` and the state `needs-info`
- **THEN** the checker exits with a failure saying clarity 4 goes to spec review

### Requirement: One question at a time

Every result SHALL have a message. A `needs-info` result's message SHALL ask exactly one question.

#### Scenario: Two questions at once

- **WHEN** a `needs-info` result's message is "Which page? And should it show past shows?"
- **THEN** the checker exits with a failure saying to ask one question

#### Scenario: No question

- **WHEN** a `needs-info` result's message is "I need to know more about this."
- **THEN** the checker exits with a failure saying to ask one question

#### Scenario: No message

- **WHEN** a result's message is empty or missing
- **THEN** the checker exits with a failure saying the message is missing

### Requirement: Messages stay on the issue

A result's message SHALL mention no GitHub user, an `@` followed by a login at the start of a word, and SHALL be at most 2,000 characters, so a result can't notify people or flood the issue. An email address isn't a mention.

#### Scenario: A mention

- **WHEN** a result's message contains `@sooz`
- **THEN** the checker exits with a failure saying messages mention no one

#### Scenario: An email address

- **WHEN** a `spec-review` result's message says artists can write to booking@venue.com
- **THEN** the checker accepts it

#### Scenario: Too long

- **WHEN** a result's message is 2,001 characters long
- **THEN** the checker exits with a failure saying the message is too long

### Requirement: The prompts state the rules

Each workflow's prompt SHALL tell the agent:
- to take the OpenSpec explore stance;
- the labels it may use;
- the states it may choose;
- the clarity rule;
- to ask exactly one question;
- how to recognise the bridge's own comments;
- to change no file but the result;
- where to write the result.

#### Scenario: Prompt rules

- **WHEN** the configuration tests read each prompt
- **THEN** it names the explore stance in those words ("explore stance"), `.intentable/result.json`, the label groups that workflow may give, the states that workflow may choose, the clarity threshold of 4, the bridge's marker `<!-- intentable-bridge -->`, and the instructions to ask exactly one question and to change no other file

### Requirement: A guide explains the workflows

`docs/FABRO.md` SHALL describe what `triage` and `clarify` do, which issues start them, and how to try one by hand against a test branch.

#### Scenario: Guide sections

- **WHEN** the configuration tests read `docs/FABRO.md`
- **THEN** it has a section for each workflow, and its command for trying one passes `--environment daytona` and `--target natea/newenglandmusic@<branch>`
