## Purpose

Configure Fabro workflows for this repo, so agents can work on the site in sandboxes that use a Claude subscription token, against the fork and never the upstream repository.

## ADDED Requirements

### Requirement: Runs target the fork, never upstream

The project configuration SHALL name natea/newenglandmusic as the repository for every Daytona run, so that a Daytona run started from this checkout without `--target`, whose `origin` is nycnoise/nycnoise, stops instead of pushing to or opening anything against upstream. No file under `.fabro/` SHALL name nycnoise/nycnoise, and every `fabro run` command for a Daytona workflow in the guide SHALL pass `--target natea/newenglandmusic`. Local runs need no target: Fabro rejects `--target` for them and works from the checkout's committed files.

#### Scenario: Project names the fork

- **WHEN** the configuration tests read `.fabro/project.toml`
- **THEN** it sets the run's source control repository to provider `github`, owner `natea` and repository `newenglandmusic`

#### Scenario: A setting names upstream

- **WHEN** any file under `.fabro/` names nycnoise/nycnoise
- **THEN** the configuration tests fail

#### Scenario: Guide commands name the fork

- **WHEN** the configuration tests read every `fabro run` command in the guide
- **THEN** each command that uses a Daytona workflow passes `--environment daytona` and `--target natea/newenglandmusic`

### Requirement: Smoke-test runs push nothing and open no pull request

The `hello` and `claude-max` workflows SHALL NOT push a run branch or open a pull request.

#### Scenario: Smoke-test settings

- **WHEN** the configuration tests read the two workflows' settings
- **THEN** both disable pull requests and run-branch pushing

### Requirement: A hello workflow checks the setup without a model

The repo SHALL have a `hello` workflow that runs one shell command and no model step, in the local environment, for checking that the Fabro server and the repo configuration work without using any model provider.

#### Scenario: Hello workflow shape

- **WHEN** the configuration tests read the `hello` workflow
- **THEN** its graph has exactly one step between start and exit, that step is a command with no prompt, and the workflow names no model or provider

### Requirement: Claude Code runs in a Daytona sandbox with a subscription token

The repo SHALL define a `daytona` environment, in which Claude Code runs through Fabro's ACP backend, in `.fabro/environments/daytona.json`: the request body Fabro's environments API takes, including the sandbox's Dockerfile inline. Claude Code SHALL authenticate with the subscription token stored in Fabro's secret vault as `CLAUDE_CODE_OAUTH_TOKEN`, with `ANTHROPIC_API_KEY` set empty in the sandbox, so that a missing token fails the Claude Code step, naming the missing secret, instead of falling back to an API key. No file in the repo SHALL contain a token value.

#### Scenario: Token comes from the vault

- **WHEN** the configuration tests read the `daytona` environment
- **THEN** `CLAUDE_CODE_OAUTH_TOKEN` is exactly the vault reference `{{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}`, `ANTHROPIC_API_KEY` is empty, and no other Anthropic credential is referenced

#### Scenario: No token in the repo

- **WHEN** the configuration tests scan the tracked files in the repo
- **THEN** none contains a token-shaped value: `sk-ant-`, then a token type of letters and digits such as `oat01`, a hyphen, and at least 20 key characters

### Requirement: A failed step fails the run

The `hello` and `claude-max` workflows SHALL end the run as failed when any step fails, instead of continuing to exit and reporting success.

#### Scenario: Failure policy

- **WHEN** the configuration tests read the two workflows' graphs
- **THEN** each sets the graph-level failure policy `on_failure="exit"`

### Requirement: The repo's environment definition is what the server runs

Fabro runs use only environments stored on the Fabro server. The repo SHALL have a script, `bin/fabro-environment`, that creates the `daytona` environment on the server from `.fabro/environments/daytona.json` when the server has none of that name, and replaces it when it has one, so the server runs what the repo defines. The script SHALL send the server's dev token in a request header read from a file, never on a command line, and SHALL NOT print it.

#### Scenario: Environment missing on the server

- **WHEN** the script runs and the server answers that no `daytona` environment exists
- **THEN** it creates one with the file's contents, and exits successfully

#### Scenario: Environment already on the server

- **WHEN** the script runs and the server returns an existing `daytona` environment with its revision
- **THEN** it replaces that environment with the file's contents, without the `id` field, passing the revision it was given, and exits successfully

#### Scenario: The dev token stays off command lines

- **WHEN** the script calls the server
- **THEN** no command it runs has the dev token among its arguments, and nothing it prints contains the token

### Requirement: Smoke-test sandboxes stop when idle

The `daytona` environment used by this change SHALL stop a sandbox when its run ends and after at most 30 minutes of inactivity, and SHALL NOT preserve sandboxes. Later workflows that need longer-lived sandboxes, such as previews, define their own environments.

#### Scenario: Lifecycle settings

- **WHEN** the configuration tests read the `daytona` environment
- **THEN** it stops on terminal status, auto-stops after 30 minutes or less, and does not preserve sandboxes

### Requirement: A claude-max workflow exercises the sandbox path

The repo SHALL have a `claude-max` workflow with exactly one Claude Code step, run through the ACP backend, that writes `hello-claude-max.txt` to the workspace. It runs in the `daytona` environment, which the run command selects with `--environment daytona`, because Fabro does not apply an environment chosen in a workflow's settings.

#### Scenario: Claude-max workflow shape

- **WHEN** the configuration tests read the `claude-max` workflow
- **THEN** its graph has exactly one step between start and exit, that step is an agent using the ACP backend with the `claude-code-acp` command, and its prompt names `hello-claude-max.txt`

### Requirement: A guide explains how to run the workflows

The repo SHALL have a guide at `docs/FABRO.md` that, for each workflow, says what it proves and gives the exact command to run it, and gives the one-time steps for the subscription token without putting the token in a command line.

#### Scenario: Guide covers both workflows and the token

- **WHEN** the configuration tests read `docs/FABRO.md`
- **THEN** it names both `hello` and `claude-max` with a `fabro run` command for each, includes `claude setup-token` and `bin/fabro-environment`, and stores the token with `fabro secret set CLAUDE_CODE_OAUTH_TOKEN` followed by no value
