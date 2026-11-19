## MODIFIED Requirements

### Requirement: The agent's record of the build is checked

The finish step SHALL fail the run when the agent's record of the build is missing or malformed: an outcome other than `complete` or `stopped`, a change with no folder under `openspec/changes/`, a message that is empty, over 2000 characters, or has an `@` mention outside code (the rules of `bin/check-intentable-result`, except that a mention inside backticks is allowed), a task listed as needing a person that isn't an unticked task, or a `preview` that isn't a list of at most 8 pages, each a `path` on the site from its root (starting with `/` but not `//`, with no spaces, at most 200 characters) and a `check` of at most 120 characters saying what to look at there.

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

#### Scenario: Pages to check

- **WHEN** the agent's record names `{"path": "/discover/", "check": "the Start button over the thumbnail"}` in `preview`
- **THEN** the finish step accepts it

#### Scenario: A page that isn't on the site

- **WHEN** the agent's record names `https://example.com/` as a page in `preview`
- **THEN** the finish step fails the run with the reason

### Requirement: The result is what the bridge reads

The finish step, and only the finish step, SHALL write `.intentable/result.json` with:
- `labels`: an empty list;
- `state`: null;
- `message`: the agent's message;
- `outcome`: `complete` or `stopped`;
- `change`: the change built;
- `preview`: the pages the agent named for checking the pull request's preview, when it named any (see `preview` in the agent's record).

It SHALL copy the agents' summary to `.intentable/pull-request.md`, adding the tasks left for a person. With no summary and no task left for a person, it SHALL leave that file out without failing the run, since the bridge opens the pull request without one.

#### Scenario: The written result

- **WHEN** the finish step checks a complete build of `export-venues-csv`
- **THEN** `.intentable/result.json` is `{"labels": [], "state": null, "message": "…", "outcome": "complete", "change": "export-venues-csv"}`, and `.intentable/pull-request.md` holds the agents' summary

#### Scenario: No summary

- **WHEN** the agents wrote no summary and left no task for a person
- **THEN** the finish step writes the result and no `.intentable/pull-request.md`

#### Scenario: Pages in the result

- **WHEN** the agent's record of a complete build names `/discover/` in `preview`
- **THEN** `.intentable/result.json` carries the same `preview` list, which intentable's bridge links from the preview's comment
