## MODIFIED Requirements

### Requirement: Triage and clarify workflows exist

The repo SHALL have a `triage` and a `clarify` workflow in `.fabro/workflows/`. Each SHALL install Claude Code at pinned versions, then run it as an ACP agent with the workflow's prompt, then check the result, going back to the agent when the check refuses it.

#### Scenario: Workflow shape

- **WHEN** the configuration tests read the `triage` and `clarify` workflows
- **THEN** each runs, in order, an install step with pinned Claude Code and ACP adapter versions, an ACP agent step whose prompt is the workflow's `prompt.md`, and a step that runs `bin/check-intentable-result` with the workflow's name, with one more edge, from the check step back to the agent step, taken only when the check fails

### Requirement: A run ends with its result

Neither workflow SHALL wait for a person: a question for the person who asked is the run's result. A failed step SHALL end the run as failed, except a refused result, which goes back to the agent while the agent step has visits left.

#### Scenario: No human gate

- **WHEN** the configuration tests read the two graphs
- **THEN** neither has a human gate step, and both set `on_failure="exit"`

### Requirement: The prompts state the rules

Each workflow's prompt SHALL tell the agent:
- to take the OpenSpec explore stance;
- the labels it may use;
- the states it may choose;
- the clarity rule;
- to ask exactly one question;
- how to recognise the bridge's own comments;
- to change no file but the result;
- where to write the result;
- what to do when `.intentable/refused.txt` says the check refused its last result.

#### Scenario: Prompt rules

- **WHEN** the configuration tests read each prompt
- **THEN** it names the explore stance in those words ("explore stance"), `.intentable/result.json`, the label groups that workflow may give, the states that workflow may choose, the clarity threshold of 4, the bridge's marker `<!-- intentable-bridge -->`, the instructions to ask exactly one question and to change no other file, and `.intentable/refused.txt`

### Requirement: A guide explains the workflows

`docs/FABRO.md` SHALL describe what `triage` and `clarify` do, which issues start them, how a refused result goes back to the agent, and how to try one by hand against a test branch.

#### Scenario: Guide sections

- **WHEN** the configuration tests read `docs/FABRO.md`
- **THEN** it has a section for each workflow, it names `.intentable/refused.txt`, and its command for trying one passes `--environment daytona` and `--target natea/newenglandmusic@<branch>`

## ADDED Requirements

### Requirement: A refused result goes back to the agent

When the check refuses a triage or clarify result, the run SHALL go back to the agent step, at most twice, so the agent step runs at most three times. Each time, the agent SHALL find the check's reason in `.intentable/refused.txt`. When the agent step has no visits left and the check refuses again, the run SHALL end as failed.

#### Scenario: The visit limit

- **WHEN** the configuration tests read the `triage` and `clarify` workflows
- **THEN** each sets `max_visits=3` on the agent step

#### Scenario: Refused, then fixed

- **WHEN** the checker runs on a clarify result whose message has two question marks, then on the agent's fixed result with one
- **THEN** it refuses the first and writes `.intentable/refused.txt`, then accepts the second and removes the file

### Requirement: The check writes down why it refused

When `bin/check-intentable-result` refuses a triage or clarify result, including a missing one, it SHALL write the reason it gives, without the `result refused:` prefix it prints, to `refused.txt` in the folder of the result file it checked, `.intentable/` by default, creating that folder if it isn't there. When it accepts one, it SHALL remove that file if it is there. It SHALL NOT write the file for a spec draft.

#### Scenario: A refusal

- **WHEN** the checker refuses a clarify result whose message has two question marks
- **THEN** `.intentable/refused.txt` holds "ask one question: the message must have exactly one question mark", and the checker exits with a failure

#### Scenario: A missing result after a refusal

- **WHEN** `.intentable/refused.txt` is there and the checker runs with no `.intentable/result.json`
- **THEN** the file says the result is missing, and the checker exits with a failure

#### Scenario: Accepted after a refusal

- **WHEN** `.intentable/refused.txt` is there and the checker accepts a triage result
- **THEN** the file is gone, and the checker exits with success

#### Scenario: A spec draft

- **WHEN** the checker refuses a spec draft
- **THEN** it writes no `.intentable/refused.txt`
