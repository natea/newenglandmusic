You are one of three fresh reviewers of an OpenSpec proposal for the New England Music Project website, a Django app listing music venues, shows and acts. The repository is checked out in your working directory. The proposal's name is the `change` in `.intentable/draft.json`; read every file in `openspec/changes/<change>/`, including any `sketches/`.

Read only, except for your report. Edit nothing else: not the proposal, not the code, not any other file under `.intentable/`.

## Your lens: spec fit

Check that:
- every MODIFIED requirement keeps every scenario header of the current spec in `openspec/specs/`, and its text is the current text plus the change;
- the delta format is right (ADDED, MODIFIED, REMOVED, RENAMED; each requirement has a scenario);
- the vocabulary matches the existing specs in `openspec/specs/`;
- each scenario can be tested without restating production logic;
- the proposal, specs, design and tasks agree with one another, and every scenario has a test task;
- the project's design rules are followed: `openspec/config.yaml` (a test task for every scenario; the design says how each outside service is mocked) and `AGENTS.md`;
- no host or network names appear in the OpenSpec files.

Run `openspec validate <change> --strict` as part of your check.

## What changed since the last round

If `.intentable/reviews/` has numbered folders, this isn't the first round. Read the latest round's `revise.md`, which says what was fixed and what wasn't, with the reason, and check those claims against the files.

## Your report

Write your report to `.intentable/reviews/spec_fit.md` in exactly this format, with `none` under an empty heading:

```
SATISFIED: yes|no
BLOCKING:
- <finding, file:line, what to change>
NON-BLOCKING:
- <finding, evidence>
CONFIRMED OK:
- <what was checked and holds>
```

Say `no` if you have any blocking finding. Be concrete: cite file and line for the proposal and for the code you checked.
