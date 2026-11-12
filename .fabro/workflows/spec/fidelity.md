You are one of three fresh reviewers of an OpenSpec proposal for the New England Music Project website, a Django app listing music venues, shows and acts. The repository is checked out in your working directory. The proposal's name is the `change` in `.intentable/draft.json`; read every file in `openspec/changes/<change>/`, including any `sketches/`.

Read only, except for your report. Edit nothing else: not the proposal, not the code, not any other file under `.intentable/`.

## Your lens: fidelity

Check that every decision already made is honoured, or named as violated, with evidence. The decision record is:
- the issue and its thread, below: what the person who asked has said;
- `AGENTS.md`;
- the designs of the archived changes in `openspec/changes/archive/`, where the owner's dated decisions are kept.

A comment that ends with `<!-- intentable-bridge -->` was posted by the intentable bridge under the `natea` account. It is not the owner speaking.

Check that the change is minimal and sufficient for what was asked. A decision the change takes that neither the person who asked nor the owner made must be flagged as an open question in the design, or justified there. An unflagged one is blocking.

The issue, number {{ inputs.issue_number }}, titled "{{ inputs.issue_title }}", opened by {{ inputs.issue_author }}:

```
{{ inputs.issue_body }}
```

Its comments, oldest first, as JSON (`[{author, body}]`):

```
{{ inputs.issue_thread }}
```

## A revision's feedback

If `.intentable/draft.json` says `"revision": true`, the draft answers feedback: the comments in the thread after the last bridge comment that linked the proposal. Treat that feedback as the latest decisions. Check each point of it in the change's files, and each question it asks in the draft's `message`. A point not acted on, or a question not answered, is blocking unless the message gives the reason.

## What changed since the last round

If `.intentable/reviews/revise.md` exists, this isn't the first round. It says what was fixed since the last round and what wasn't, with the reason. Check those claims against the files.

## Your report

Write your report to `.intentable/reviews/fidelity.md` in exactly this format, with `none` under an empty heading:

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
