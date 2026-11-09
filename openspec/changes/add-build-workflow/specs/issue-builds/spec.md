## Purpose

The `build` workflow the intentable bridge starts once Nate confirms a proposal: it applies the change on its draft branch one task group at a time, makes a refactoring pass, checks its own commits, and leaves a result and a pull request summary for the bridge.

## ADDED Requirements

### Requirement: A build workflow exists

The repository SHALL have a `build` workflow in `.fabro/workflows/build/`, whose graph runs, in order: setup, apply, a route, then either refactor and the final check or the final check alone. A failed step SHALL end the run as failed.

#### Scenario: The build graph

- **WHEN** the configuration tests read `.fabro/workflows/build/workflow.fabro`
- **THEN** it has the steps setup, apply, route, refactor and finish, with an edge from route to refactor and one from route to finish, and sets `on_failure="exit"`

#### Scenario: The graph is valid

- **WHEN** `fabro validate` reads the build graph
- **THEN** it passes

### Requirement: The build takes the issue and its change as inputs

The `build` workflow SHALL declare the inputs `issue_number`, `issue_title`, `issue_body`, `issue_author`, `issue_thread` and `change_name`, each with an empty default, and its agents SHALL be given the change's name from `change_name`.

#### Scenario: Declared inputs

- **WHEN** the configuration tests read the build's `workflow.toml`
- **THEN** it declares exactly those six inputs, each defaulting to an empty string

#### Scenario: The apply prompt names the change

- **WHEN** the configuration tests read the apply prompt
- **THEN** it contains `{{ inputs.change_name }}` and the five issue inputs

### Requirement: No input reaches a command

No command step of the `build` workflow SHALL contain an input, so neither issue text nor the change's name can run as a shell command in the sandbox.

#### Scenario: Commands without inputs

- **WHEN** the configuration tests read every command step of the build graph
- **THEN** none contains `{{ inputs.`

### Requirement: The build is self-contained

No command step of the `build` workflow SHALL run one of the repository's own scripts under `bin/`, since the checkout is the change's draft branch, which can predate this workflow. The build's checks SHALL be inline in its graph, and the rules its agents follow SHALL be in its prompts.

#### Scenario: No script from the checkout

- **WHEN** the configuration tests read every command step of the build graph
- **THEN** none refers to `bin/`

#### Scenario: The refactoring rules travel with the workflow

- **WHEN** the configuration tests read the refactor prompt
- **THEN** it states the refactoring rules itself and refers to no file under `_workflows/`

### Requirement: Every build agent runs through ACP on the subscription

Every agent step of the `build` workflow SHALL be Claude Code through ACP (`backend="acp"`, `acp.command="claude-agent-acp"`), so it runs on Nate's Max subscription through the `daytona` environment, never on an API key.

#### Scenario: ACP agents only

- **WHEN** the configuration tests read the build graph
- **THEN** apply and refactor are ACP agents, and no step is a Fabro prompt stage

### Requirement: The run branch is pushed and no pull request is opened

The `build` workflow SHALL push its run branch (`[run.run_branch] push = true`) and open no pull request (`[run.pull_request] enabled = false`). It SHALL collect `.intentable/result.json` and `.intentable/pull-request.md` as artifacts.

#### Scenario: Build settings

- **WHEN** the configuration tests read the build's `workflow.toml`
- **THEN** the run branch is pushed, the pull request is off, and the artifacts include exactly those two files

#### Scenario: The other workflows still push nothing

- **WHEN** the configuration tests read the triage, clarify and spec settings
- **THEN** each still pushes no run branch and opens no pull request

### Requirement: Setup installs what the tests need

The setup step SHALL install Claude Code, its ACP adapter and `openspec` at pinned versions, Python 3.11 with the dev requirements, a running local Postgres, and Chromium for the browser test, and compile the CSS, as CI does. It SHALL record the commit the run started from in `.intentable/`, so later checks know what the run added.

#### Scenario: Setup's tools

- **WHEN** the configuration tests read the setup step
- **THEN** it pins `@anthropic-ai/claude-code`, `@agentclientprotocol/claude-agent-acp` and `@fission-ai/openspec` to exact versions, installs Python 3.11, `requirements-dev.txt`, Postgres and Chromium, runs `compilescss`, and writes the starting commit under `.intentable/`

### Requirement: Apply commits one task group at a time, only on green

The apply agent SHALL work through the change's `tasks.md` one `## N.` group at a time. For each group, it SHALL make the group's changes, tick the group's boxes, run the whole suite, and commit once with the group's work and ticks, only when the suite passes (rule G3). The apply prompt SHALL say so.

#### Scenario: The apply prompt states the commit rule

- **WHEN** the configuration tests read the apply prompt
- **THEN** it says to commit one group at a time with its boxes ticked in the same commit, and never on a failing suite

### Requirement: Apply stops at a group it can't make pass

If a group can't be made to pass, the apply agent SHALL commit nothing for that group, stop, and record the outcome `stopped` with a plain reason for the person who asked. Otherwise it SHALL record `complete`. The apply prompt SHALL say so.

#### Scenario: The apply prompt says when to stop

- **WHEN** the configuration tests read the apply prompt
- **THEN** it says to stop at a group that can't pass, commit nothing for it, and record `stopped` with the reason

### Requirement: The build agents keep to what the bridge accepts

The apply and refactor prompts SHALL each forbid merge commits, pushing, closing keywords in commit messages, any change under `.github/` or `.fabro/` or to `bin/publish-spek-page`, and subagents or background tasks.

#### Scenario: The forbidden list

- **WHEN** the configuration tests read the apply and refactor prompts
- **THEN** each forbids merges, pushes, closing keywords, the protected paths and subagents, and says to leave no uncommitted change behind, discarding a group it stops at

### Requirement: The agents leave nothing uncommitted

Fabro commits whatever a step leaves changed, so the apply and refactor agents SHALL end with a clean working tree: every change committed under the rules above, and a group the agent stopped at discarded. The setup step SHALL change no tracked file, and SHALL fail the run if it did.

#### Scenario: The prompts say to leave a clean tree

- **WHEN** the configuration tests read the apply and refactor prompts
- **THEN** each says to end with a clean working tree, discarding the changes of a group it stops at

#### Scenario: Setup checks the tree

- **WHEN** the configuration tests read the setup step
- **THEN** it ends by failing when `git status --porcelain` lists anything

### Requirement: A stopped build skips the refactoring pass

The route step SHALL send a build whose apply outcome is `stopped` straight to the final check, and a `complete` one to refactor.

#### Scenario: Routing on the outcome

- **WHEN** the route step reads an apply outcome of `stopped`, then one of `complete`
- **THEN** it routes the first to finish and the second to refactor

### Requirement: Refactor makes at most one commit, on green

The refactor agent SHALL review the change's code against the refactoring rules in its prompt, and SHALL make at most one commit, only when the suite passes, or none when nothing is worth changing. It SHALL change no behaviour the specs describe, and SHALL follow the same forbidden list as apply.

#### Scenario: The refactor prompt states the rules

- **WHEN** the configuration tests read the refactor prompt
- **THEN** it says to make at most one commit, only on a passing suite, to change no specified behaviour, and forbids merges, pushes, closing keywords, the protected paths and subagents

### Requirement: The final check fails a build whose commits broke the rules

The finish step SHALL fail the run, naming the commit, when a commit since the run's starting commit is a merge, is a checkpoint commit Fabro made of work an agent left uncommitted, has a closing keyword followed by an issue reference in its message, or adds, changes, removes or renames a file under `.github/` or `.fabro/`, or `bin/publish-spek-page`.

#### Scenario: A clean complete build

- **WHEN** the finish step checks a run with two task-group commits and a refactoring commit, every box ticked, and a passing suite
- **THEN** it writes the result and exits 0

#### Scenario: A merge commit

- **WHEN** one of the run's commits is a merge
- **THEN** the finish step fails the run and names the commit

#### Scenario: Work left uncommitted

- **WHEN** one of the run's commits is Fabro's checkpoint commit `fabro(<run-id>): apply (succeeded)`
- **THEN** the finish step fails the run and names the commit

#### Scenario: A closing keyword

- **WHEN** one of the run's commit messages says "Closes: #3"
- **THEN** the finish step fails the run and names the commit

#### Scenario: A protected file

- **WHEN** one of the run's commits renames `.fabro/workflows/build/apply.md`
- **THEN** the finish step fails the run and names the commit and the path

### Requirement: The final check fails an unfinished or failing build

The finish step SHALL fail the run when the suite fails, or when a `complete` build has no commit or leaves a box unticked in the change's `tasks.md`. A `stopped` build's unticked boxes SHALL not fail it.

#### Scenario: An unticked box

- **WHEN** a complete build leaves a box unticked in the change's `tasks.md`
- **THEN** the finish step fails the run and names the task

#### Scenario: A stopped build with an unfinished group

- **WHEN** a stopped build committed one group and left the next group's boxes unticked
- **THEN** the finish step writes the result with the outcome `stopped`, and doesn't fail for the unticked boxes

#### Scenario: A failing suite

- **WHEN** the suite fails at the final check
- **THEN** the finish step fails the run

### Requirement: The agent's record of the build is checked

The finish step SHALL fail the run when the agent's record of the build is missing or malformed: an outcome other than `complete` or `stopped`, a change with no folder under `openspec/changes/`, or an empty message.

#### Scenario: A malformed record

- **WHEN** the agent's record gives the outcome `passed`, or names a change with no folder
- **THEN** the finish step fails the run with the reason

### Requirement: The result is what the bridge reads

The finish step, and only the finish step, SHALL write `.intentable/result.json` with:
- `labels`: an empty list;
- `state`: null;
- `message`: the agent's plain words for the person who asked, with no `@` mention, at most 2000 characters;
- `outcome`: `complete` or `stopped`;
- `change`: the change built.

It SHALL also write `.intentable/pull-request.md`, the agent's summary of what changed, for the pull request's body.

#### Scenario: The written result

- **WHEN** the finish step checks a complete build of `export-venues-csv`
- **THEN** `.intentable/result.json` is `{"labels": [], "state": null, "message": "…", "outcome": "complete", "change": "export-venues-csv"}`, and `.intentable/pull-request.md` holds the agent's summary

#### Scenario: A message that mentions someone

- **WHEN** the agent's message for the issue contains "@sooz"
- **THEN** the finish step fails the run

### Requirement: A guide explains the build workflow

`docs/FABRO.md` SHALL describe the `build` workflow: what starts it, its inputs and target, its steps, the rules its commits follow, what it leaves for the bridge, and how to test it from a branch.

#### Scenario: Guide section

- **WHEN** someone reads `docs/FABRO.md`
- **THEN** it has a section on the build workflow covering those points
