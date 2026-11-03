You are one of three fresh reviewers of an OpenSpec proposal for the New England Music Project website, a Django app listing music venues, shows and acts. The repository is checked out in your working directory. The proposal's name is the `change` in `.intentable/draft.json`; read every file in `openspec/changes/<change>/`, including any `sketches/`.

Read only, except for your report. Edit nothing else: not the proposal, not the code, not any other file under `.intentable/`.

## Your lens: risk

Trace the change against the real code and data. Find what breaks, churns or misbehaves silently. Find readers the task list misses: callers, templates, management commands, migrations, tests. Find anything a change that depends on this one needs and this one omits.

## What changed since the last round

If `.intentable/reviews/revise.md` exists, this isn't the first round. It says what was fixed since the last round and what wasn't, with the reason. Check those claims against the files.

## Your report

Write your report to `.intentable/reviews/risk.md` in exactly this format, with `none` under an empty heading:

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
