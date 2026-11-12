## MODIFIED Requirements

### Requirement: The build takes the issue and its change as inputs

The `build` workflow SHALL declare the inputs `issue_number`, `issue_title`, `issue_body`, `issue_author`, `issue_thread`, `change_name` and `picked_design`, each with an empty default, since the bridge sends them all. Its prompts SHALL use only `change_name`, `picked_design`, `issue_number` and `issue_title`: the confirmed proposal is the agents' instruction, and the issue's body and thread, which nobody reviewed, never reach an agent that can push.

#### Scenario: Declared inputs

- **WHEN** the configuration tests read the build's `workflow.toml`
- **THEN** it declares exactly those seven inputs, each defaulting to an empty string

#### Scenario: The prompts name the change, not the thread

- **WHEN** the configuration tests read the apply and refactor prompts
- **THEN** each contains `{{ inputs.change_name }}`, and neither uses any input other than `change_name`, `picked_design`, `issue_number` and `issue_title`

## ADDED Requirements

### Requirement: The build uses the picked sketch

When `picked_design` names a letter, `apply.md` SHALL tell the agent to build the screens from `sketches/<letter>.html` and treat the other sketches as rejected. When it is empty, the change's own artifacts decide. When that sketch is missing from the branch, the agent SHALL stop with the outcome `stopped`, saying which sketch is missing.

#### Scenario: The apply prompt names the pick

- **WHEN** the configuration tests read `apply.md`
- **THEN** it contains `{{ inputs.picked_design }}`, says to build from that sketch and not the others, and to stop when that sketch is missing
