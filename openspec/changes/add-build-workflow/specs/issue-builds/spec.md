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

### Requirement: The workflow's files are committed

No file of `.fabro/workflows/build/` SHALL be ignored by git, so the workflow reaches the fork when its branch is pushed.

#### Scenario: Nothing ignored

- **WHEN** the configuration tests ask `git check-ignore` about every file in `.fabro/workflows/build/`
- **THEN** it reports none of them

### Requirement: The build takes the issue and its change as inputs

The `build` workflow SHALL declare the inputs `issue_number`, `issue_title`, `issue_body`, `issue_author`, `issue_thread` and `change_name`, each with an empty default, since the bridge sends all six. Its prompts SHALL use only `change_name`, `issue_number` and `issue_title`: the confirmed proposal is the agents' instruction, and the issue's body and thread, which nobody reviewed, never reach an agent that can push.

#### Scenario: Declared inputs

- **WHEN** the configuration tests read the build's `workflow.toml`
- **THEN** it declares exactly those six inputs, each defaulting to an empty string

#### Scenario: The prompts name the change, not the thread

- **WHEN** the configuration tests read the apply and refactor prompts
- **THEN** each contains `{{ inputs.change_name }}`, and neither uses any input other than `change_name`, `issue_number` and `issue_title`

### Requirement: No input reaches a command

No command step of the `build` workflow SHALL contain an input, so neither issue text nor the change's name can run as a shell command in the sandbox.

#### Scenario: Commands without inputs

- **WHEN** the configuration tests read every command step of the build graph, following each script to its closing quote
- **THEN** none contains `{{`

### Requirement: The build is self-contained

No command step of the `build` workflow SHALL run a script from the repository's own `bin/` folder, since the checkout is the change's draft branch, which can predate this workflow. Paths such as `venv/bin/` and system paths are allowed. The build's checks SHALL be inline in its graph, and the rules its agents follow SHALL be in its prompts.

#### Scenario: No script from the checkout

- **WHEN** the configuration tests read every command step of the build graph
- **THEN** none runs a path that starts with `bin/`, as a command or through an interpreter

#### Scenario: Inline scripts without escapes

- **WHEN** the configuration tests read the route and finish scripts
- **THEN** neither contains a backslash or a double quote, so nothing depends on how Fabro decodes the graph's strings

### Requirement: Every build agent runs through ACP on the subscription

Every agent step of the `build` workflow SHALL be Claude Code through ACP (`backend="acp"`, `acp.command="claude-agent-acp"`), so it runs on Nate's Max subscription through the `daytona` environment, never on an API key.

#### Scenario: ACP agents only

- **WHEN** the configuration tests read the build graph
- **THEN** apply and refactor are ACP agents, and no step is a Fabro prompt stage

### Requirement: The run branch is pushed and no pull request is opened

The `build` workflow SHALL push its run branch (`[run.run_branch] push = true`), open no pull request (`[run.pull_request] enabled = false`), and ask Fabro for no GitHub permissions. It SHALL collect `.intentable/result.json` and `.intentable/pull-request.md` as artifacts. The `triage`, `clarify` and `spec` workflows SHALL still push nothing.

#### Scenario: Build settings

- **WHEN** the configuration tests read the build's `workflow.toml`
- **THEN** the run branch is pushed, the pull request is off, there is no GitHub permissions table, and the artifacts are exactly those two files

#### Scenario: The other workflows still push nothing

- **WHEN** the configuration tests read the triage, clarify and spec settings
- **THEN** each still pushes no run branch and opens no pull request

### Requirement: Setup installs what the tests need

The setup step SHALL install Claude Code, its ACP adapter and `openspec` at pinned versions, Python 3.11 with the dev requirements, a running local Postgres of version 14 or later, and Chromium for the browser test, and compile the CSS, as CI does. It SHALL write CI's test environment and the commit the run targeted under `.intentable/`, and SHALL have an explicit timeout.

#### Scenario: Setup's tools

- **WHEN** the configuration tests read the setup step
- **THEN** it pins `@anthropic-ai/claude-code`, `@agentclientprotocol/claude-agent-acp` and `@fission-ai/openspec` to exact versions, installs Python 3.11, `requirements-dev.txt`, Postgres and Chromium, checks Postgres is 14 or later, runs `compilescss`, writes `.intentable/test.env` and `.intentable/start`, and sets a `timeout`

### Requirement: Apply commits one task group at a time, only on green

The apply agent SHALL work through the change's `tasks.md` one `## N.` group at a time. For each group, it SHALL make the group's changes, tick the boxes of the tasks it did, run the whole suite, and commit once with the group's work and ticks, only when the suite passes (intentable's workflow rule G3), with a subject that says what the group did, in the repository's commit style (rule G6). The apply prompt SHALL say so.

#### Scenario: The apply prompt states the commit rule

- **WHEN** the configuration tests read the apply prompt
- **THEN** it says to commit one group at a time with its boxes ticked in the same commit, never on a failing suite, with a subject saying what the group did

### Requirement: Tasks only a person can do are left for them

A task only a person can do, which means a check by hand in a browser or a live check against an outside system, SHALL be left unticked and listed in the agent's record with the reason. The task is named in the pull request and in the message for the issue, so Nate sees it at G4. The apply prompt SHALL say so, with what qualifies, and the final check SHALL accept those listed tasks, and only those, unticked in a complete build.

#### Scenario: The apply prompt says what to leave

- **WHEN** the configuration tests read the apply prompt
- **THEN** it says to leave a task only a person can do unticked and list it with its reason, and that only a check by hand in a browser or a live check against an outside system qualifies

#### Scenario: A task left for a person

- **WHEN** a complete build leaves task 3.2 unticked and lists it in the record as needing a person
- **THEN** the finish step writes the result, and `.intentable/pull-request.md` names task 3.2, even when the agents wrote no summary

#### Scenario: A listed task that isn't left

- **WHEN** the record lists task 3.2 as needing a person, but task 3.2 is ticked or doesn't exist
- **THEN** the finish step fails the run with the reason

### Requirement: Apply stops at a group it can't make pass

If a group can't be made to pass, the apply agent SHALL commit nothing for that group, discard its changes, stop, and record the outcome `stopped` with a plain reason for the person who asked. Otherwise it SHALL record `complete`. The apply prompt SHALL say so.

#### Scenario: The apply prompt says when to stop

- **WHEN** the configuration tests read the apply prompt
- **THEN** it says to stop at a group that can't pass, commit nothing for it and discard its changes, and record `stopped` with the reason

### Requirement: The build never waits for a person

No step of the `build` workflow SHALL wait for an answer. When the apply agent needs a decision the proposal doesn't settle, it SHALL record `stopped` with the question in its message, which the bridge posts on the issue. The answer SHALL reach a retried build only through the change's own artifacts, written into them on the draft branch before the retry. The refactor agent SHALL instead leave out a change it is unsure of and note it for Nate.

#### Scenario: No question asked

- **WHEN** the configuration tests read the build graph and its prompts
- **THEN** there is no human-gate step, both prompts say never to ask and wait, the apply prompt says to stop with the question in the message and that the answer will come through the change's artifacts, and the refactor prompt says to leave the change out and note it for Nate

### Requirement: The build agents keep to what the bridge accepts

The apply and refactor prompts SHALL each forbid merge commits, pushing, closing keywords in commit messages, any change to the protected files (under `.github/` or `.fabro/`, or `bin/publish-spek-page`), an `@` in the message for the issue, and subagents or background tasks.

#### Scenario: The forbidden list

- **WHEN** the configuration tests read the apply and refactor prompts
- **THEN** each forbids merges, pushes, closing keywords, the protected files, an `@` in the message, and subagents

### Requirement: The agents leave nothing uncommitted

The apply and refactor agents SHALL end with a clean working tree: every change committed under the rules above, and a group the agent stopped at discarded. The setup and finish steps SHALL change no tracked file, and SHALL fail the run if they did.

#### Scenario: The prompts say to leave a clean tree

- **WHEN** the configuration tests read the apply and refactor prompts
- **THEN** each says to end with a clean working tree, discarding the changes of a group it stops at

#### Scenario: Setup and finish check the tree

- **WHEN** the configuration tests read the setup and finish steps
- **THEN** each ends by failing when `git status --porcelain` lists anything

### Requirement: The agents' own settings never reach a commit

A Claude Code session saves its permissions in `.claude/settings.local.json`, which the draft branch's `.gitignore` may not ignore. Setup SHALL add that file to the checkout's local exclude list, the prompts SHALL say to stage files by name and never commit it, and the finish step SHALL fail the run, naming the commit, when a commit carries it.

#### Scenario: Setup excludes the agent's settings

- **WHEN** the configuration tests read the setup step
- **THEN** it adds `.claude/settings.local.json` to the file `git rev-parse --git-path info/exclude` names

#### Scenario: The agent's settings committed

- **WHEN** one of the run's commits adds `.claude/settings.local.json`
- **THEN** the finish step fails the run and names the commit

### Requirement: A stopped build skips the refactoring pass

The route step SHALL send a build whose apply outcome is `stopped` straight to the final check, and a `complete` one to refactor.

#### Scenario: Routing on the outcome

- **WHEN** the route step reads an apply outcome of `stopped`, then one of `complete`
- **THEN** it routes the first to finish and the second to refactor

### Requirement: Refactor follows the refactoring rules it carries

The refactor agent SHALL review the change's code against the refactoring rules in its prompt, and SHALL make at most one commit, "Refactor <change>", only when the suite passes, or none when nothing is worth changing. It SHALL change no behaviour the specs describe. It SHALL not act on what the rules leave to the owner: circular dependencies and layering violations, dead code, a new grouping, or a move across a module boundary. It SHALL list those findings in the summary for Nate at G4 instead.

#### Scenario: The refactor prompt states the rules

- **WHEN** the configuration tests read the refactor prompt
- **THEN** it says to make at most one commit, only on a passing suite, to change no specified behaviour, and to report rather than fix circular dependencies, dead code, new groupings and cross-module moves, and it refers to no file under `_workflows/`

### Requirement: The final check fails a build whose commits broke the rules

The finish step SHALL fail the run, naming the commit, when a commit since the commit the run targeted:
- is a merge;
- is a Fabro checkpoint commit that changes a file, which means an agent left work behind;
- has a closing keyword followed by an issue reference in its message;
- adds, changes, removes or renames a protected file.

An empty checkpoint commit SHALL pass.

#### Scenario: A clean complete build

- **WHEN** the finish step checks a run with two task-group commits, a refactoring commit and empty checkpoint commits, every box ticked, and a passing suite
- **THEN** it writes the result and exits 0

#### Scenario: A merge commit

- **WHEN** one of the run's commits is a merge
- **THEN** the finish step fails the run and names the commit

#### Scenario: Work left uncommitted

- **WHEN** one of the run's commits is Fabro's checkpoint commit `fabro(<run-id>): apply (succeeded)` and it changes `core/views.py`
- **THEN** the finish step fails the run and names the commit

#### Scenario: A closing keyword

- **WHEN** one of the run's commit messages says "Closes: #3"
- **THEN** the finish step fails the run and names the commit

#### Scenario: A protected file

- **WHEN** one of the run's commits renames `.fabro/workflows/build/apply.md`
- **THEN** the finish step fails the run and names the commit and the path

### Requirement: The final check fails an unfinished or failing build

The finish step SHALL fail the run when the suite fails, or when a `complete` build has no commit besides Fabro's checkpoints, or leaves a box unticked in the change's `tasks.md` that isn't listed as needing a person. A `stopped` build's unticked boxes SHALL not fail it. The step SHALL have an explicit timeout.

#### Scenario: An unticked box

- **WHEN** a complete build leaves a box unticked in the change's `tasks.md`, not listed as needing a person
- **THEN** the finish step fails the run and names the task

#### Scenario: Nothing built

- **WHEN** a complete build's only commits are empty checkpoint commits
- **THEN** the finish step fails the run

#### Scenario: A stopped build with an unfinished group

- **WHEN** a stopped build committed one group and left the next group's boxes unticked
- **THEN** the finish step writes the result with the outcome `stopped`, and doesn't fail for the unticked boxes

#### Scenario: A failing suite

- **WHEN** the suite fails at the final check
- **THEN** the finish step fails the run

### Requirement: The agent's record of the build is checked

The finish step SHALL fail the run when the agent's record of the build is missing or malformed: an outcome other than `complete` or `stopped`, a change with no folder under `openspec/changes/`, a message that is empty, over 2000 characters, or has an `@` mention outside code (the rules of `bin/check-intentable-result`, except that a mention inside backticks is allowed), or a task listed as needing a person that isn't an unticked task.

#### Scenario: A malformed record

- **WHEN** the agent's record gives the outcome `passed`, or names a change with no folder
- **THEN** the finish step fails the run with the reason

#### Scenario: No record

- **WHEN** the agent wrote no record
- **THEN** the finish step fails the run

#### Scenario: A message that breaks the rules

- **WHEN** the agent's message is empty, is over 2000 characters, or contains "@sooz"
- **THEN** the finish step fails the run

#### Scenario: Code in the message

- **WHEN** the agent's message mentions `` `@admin.register` `` in backticks
- **THEN** the finish step accepts it

### Requirement: The result is what the bridge reads

The finish step, and only the finish step, SHALL write `.intentable/result.json` with:
- `labels`: an empty list;
- `state`: null;
- `message`: the agent's message;
- `outcome`: `complete` or `stopped`;
- `change`: the change built.

It SHALL copy the agents' summary to `.intentable/pull-request.md`, adding the tasks left for a person. With no summary and no task left for a person, it SHALL leave that file out without failing the run, since the bridge opens the pull request without one.

#### Scenario: The written result

- **WHEN** the finish step checks a complete build of `export-venues-csv`
- **THEN** `.intentable/result.json` is `{"labels": [], "state": null, "message": "…", "outcome": "complete", "change": "export-venues-csv"}`, and `.intentable/pull-request.md` holds the agents' summary

#### Scenario: No summary

- **WHEN** the agents wrote no summary and left no task for a person
- **THEN** the finish step writes the result and no `.intentable/pull-request.md`

### Requirement: A guide explains the build workflow

`docs/FABRO.md` SHALL describe the `build` workflow: what starts it and what it targets, its steps and commit rules, what its final check refuses, what it leaves for the bridge, how to answer a stopped build's question, and how to test it from a branch. Any by-hand `fabro run` command it gives SHALL name the fork and the `daytona` environment.

#### Scenario: Guide section

- **WHEN** the tests read `docs/FABRO.md`
- **THEN** it has a build workflow section that mentions `/approve`, `change_name`, `change/<name>`, `outcome`, `stopped`, `pull-request.md`, `retry-build.ts` and `FABRO_WORKFLOW_REF`, and every `fabro run` line in it names `natea/newenglandmusic` and `--environment daytona`
