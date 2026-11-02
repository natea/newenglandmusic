## Context

`triage` and `clarify` (archived as `2026-11-02-add-triage-clarify`) leave an issue in `spec-review` with a summary. The intentable bridge starts runs over Fabro's API, in the `daytona` environment, targeting a commit of natea/newenglandmusic. It reads a run's `.intentable/result.json` from its artifacts, applies the result, and deletes the run's sandboxes. Nate's rules apply here too:
- runs read the code and push nothing;
- every run ends with its result;
- drafts are published before G2 on a `change/<name>` branch with "Draft" in the commit subject, so their Spek page builds (`AGENTS.md`, `spec-pages`).

The review loop is the `dev-review-proposal` skill from intentable: three fresh reviewers, one lens each, revising until all three are satisfied on one revision.

## Goals / Non-Goals

**Goals:**
- An issue in `spec-review` gets a complete OpenSpec change, passed by three reviewers or marked as not passed, without any person's input during the run.
- The draft reaches a `change/` branch, and so its Spek page, with no GitHub write access in the sandbox.

**Non-Goals:**
- Starting the run and committing the draft. Those are the bridge's job, in intentable's `add-spec-runs`.
- G2 through the issue, moves out of `spec-review`, revising a draft after Nate comments, and Impeccable sketches.

## Decisions

**The graph.**

```
start -> install -> propose -> check_draft -> fork
fork -> risk, spec_fit, fidelity -> merge -> check_reviews
check_reviews -> finish   [outcome=succeeded]   (all yes, or round limit reached)
check_reviews -> revise   (otherwise)
revise -> check_draft      (the reviewers run again on the revised text)
finish -> exit
```

- **`install`** pins Claude Code and the ACP adapter at the versions `triage` uses, and `@fission-ai/openspec` at 1.16.0, the version this repository's artifacts were written with. It also writes the names of every folder in `openspec/changes/` and `openspec/changes/archive/` to `.intentable/existing-changes.txt`. That record is how the checker later tells a new change from an existing one. The record is made before the agent runs, because Fabro's local checkpoint commits make the checkout's `HEAD` an unreliable base.
- **`check_draft`** runs `bin/check-intentable-result spec --draft`: the name rules and `openspec validate --strict`. Its failure ends the run, like every failed step (`on_failure="exit"`). An invalid draft is never shown to reviewers.
- **`check_reviews`** is `bin/check-intentable-reviews`. It keeps the round number in `.intentable/reviews/round`, and moves each round's reports to `.intentable/reviews/<round>/` so revise and the summary can read every round. It exits 0 when the loop should end, and 1 when another round is needed. The edge into `revise` must therefore be the graph's failure route, not the `on_failure="exit"` default. Task 1.1 checks with `fabro validate` and a dry graph that a conditional edge on `outcome` overrides `on_failure="exit"`. If it doesn't, the script instead writes `context.review_done` and the edges branch on that, with the script always exiting 0.
- **Reviewers run in one checkout** (Fabro's fan-out shares it), and each writes only its own report file, so there is no race. Each is a separate agent node, and therefore a fresh session: it hasn't seen the propose agent's reasoning, only the files. This matches the skill's rule that the author's conclusions aren't in the brief.

**Briefs.** Each reviewer prompt gives its lens, the change folder path, `openspec/specs/`, `AGENTS.md` and `openspec/config.yaml`, the issue thread as the record of the requester's decisions, and the report format. There is no project dictionary in this repo, so spec fit checks vocabulary against the existing specs. The fidelity lens has no memory file in the sandbox. Its sources are the thread and `AGENTS.md`. A decision the proposal takes that neither settles must be flagged as an open question in the design.

**Round limit: 3** (decision taken without Nate, about 80% likely to be his; the skill itself sets no limit). The limit caps cost. A run that hits it still ends with its draft, because a draft with open findings is more use to Nate than a failed run. `review.md` and the bridge's message both say it wasn't passed.

**The result.**
- `labels` may carry `needs-design`, the one later-stage label this stage knows about. The plan says `needs-design` routes the issue to Impeccable.
- `state` is always none. The issue leaves `spec-review` only at G2, which a later change builds.
- `finish` runs `bin/check-intentable-result spec`: the result's rules, the draft checks again, a 90-file cap under Fabro's 100-file collection limit (leaving room for the result and the summary), and the copy into `.intentable/proposal/`. The copy is made last, so the collected proposal is the final text only. Fabro records each artifact path once per content, and earlier drafts never sat under that path.

**Name rule.** The name is `^[a-z0-9]+(-[a-z0-9]+)*$`, at most 60 characters. That is the same set `bin/publish-spek-page` accepts for a change page. The checker passes it to `openspec` only as a separate argument, never through a shell.

**Testing.** No external service is called in tests:
- the configuration tests read the workflow files;
- the checkers are run as subprocesses on temporary folders holding fixture changes and reports;
- `openspec` is run for real, since it is a local, pinned CLI;
- Fabro, Claude and GitHub aren't touched;
- the live check on the Spark is a manual task.

## Risks / Trade-offs

- **[Cost]** Up to 13 agent sessions a run. → The round limit; the bridge starts one `spec` run per issue.
- **[A reviewer is too harsh or never satisfied]** → The limit ends the loop with the draft and its findings for Nate.
- **[The agent edits code]** The prompt forbids it. Only `.intentable/proposal/` leaves the sandbox, and that holds only the change folder, so a stray edit elsewhere never leaves the sandbox.
- **[Issue text steering the agent]** As with `triage`: inputs never reach a command, the sandbox has read-only git, and the result is checked before the bridge uses it.

## Open Questions

- Should the round limit be 3, or should the run fail instead when the reviewers don't agree?
- Should the agent also be able to say an issue isn't ready for a proposal after all (a question back to `needs-info`)? This change leaves it out: once in `spec-review`, the agent writes the best proposal it can and records the gaps as open questions.
