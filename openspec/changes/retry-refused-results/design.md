## Context

Both graphs are `install -> think -> check -> exit` with `on_failure="exit"`, so a refusal by `check` ends the run. `bin/check-intentable-result` prints one plain reason and exits 1. Fabro routes a failed step along an edge whose `condition="outcome=failed"` before the graph's `on_failure` applies (docs: workflows/transitions, "explicit recovery routes take priority under every policy"), and `max_visits` on a node bounds how often it runs; going past it ends the run as failed (execution/failures). Fabro keys each stage's artifacts by its stage ID, which includes the visit (`think@1`, `think@2`), and a retry count that starts again at 1 for each visit (`fabro-store`'s `ArtifactKey`).

## Goals / Non-Goals

**Goals:** an agent that slips on a rule gets to fix it without Nate; nothing about a run that passes first time changes.

**Non-Goals:** the agent noticing its own slips before the check (the prompts already tell it the rules; the check is the backstop); retrying runs that fail for other reasons, such as a sandbox or install failure.

## Decisions

**The reason travels in a file, not in Fabro's preamble.** Fabro gives a returning agent step a summary of earlier stages (fidelity `compact`, the default), which may or may not carry the check's output, and the docs don't say. A file the check writes, in the sandbox both steps share, doesn't depend on that: `.intentable/refused.txt`, which the prompt names. `.intentable/` is git-ignored, and the workflows collect only `result.json`, so it never reaches the bridge or a commit. The check removes it on accepting, so a passing run never leaves one behind. The alternative, `fidelity="full"` on the back edge so the agent continues its own conversation, saves the agent re-reading the issue but still wouldn't show it the command's output.

**The graph:**

```
start -> install -> think -> check -> exit
check -> think [condition="outcome=failed"]
```

with `max_visits=3` added inside the existing `think [...]` and `check [...]` blocks. On `check` it keeps `fabro validate` from warning about a loop with no limit, and changes nothing else, since `check` can't run more often than `think`. A second `think [...]` statement would replace the first in the tests' step parser (`core/tests/test_fabro_config.py`).

`check -> exit` stays unconditional; under `on_failure="exit"` it is taken only on success, since the conditioned edge takes the failure. "Up to two tries" is read as two more visits after the first, three in all. With three visits, a result refused three times ends the run as failed, as today, and the bridge reports it the same way.

**The prompt section** comes first in each prompt, so a returning agent reads it before starting over: "If `.intentable/refused.txt` exists, the check refused your last result for the reason it gives. Read `.intentable/result.json`, fix what the reason names, and write it again. Keep your decision, the labels and the state, unless the reason is about them. Change nothing else." The rest of the prompt still applies. Most refusals are about the message, such as the one-question rule or the spec-review ending. A few are about the decision itself: "clarity N needs a question, not spec review" and its opposite can only be fixed by changing the state. So the agent may change the labels or the state only when the reason names them. Everything else stays as it was, so a retry can't quietly redo the triage.

**Where the file goes.** Beside the result file checked, so the default is `.intentable/refused.txt`, and a by-hand run on `path/to/result.json` writes `path/to/refused.txt`, never into the working directory. The checker creates the folder if it isn't there. A missing result is a refusal like any other, so a second visit that writes nothing still leaves its reason for the third.

**Tests** call no outside service: the checker runs on temporary folders, and the `fabro validate` test is skipped where `fabro` isn't installed.

**Writing the file only for triage and clarify.** The spec workflow's checks keep ending the run (proposal, out of scope), so `check_spec` writes nothing. The file is written by `main` around the triage and clarify check, so `check()` stays a pure function and its tests don't change.

**intentable's `latestResult`** sorts the run's `result.json` entries by the visit in `stage_id` (the number after `@`, compared as a number), then by `retry`, both descending. Fabro returns artifacts in ascending order and the sort is stable, so today's code picks `think@1` on a tie. It assumes one step writes the result, as every workflow does today. intentable's `run-status` spec says the bridge reads "that step's highest retry" of the last step, so that changes too, in a small intentable change (task 1.1). Today's single-visit runs pick the same entry as before. It is a separate commit on an intentable branch, deployed before this change reaches the fork's `main`, because a run with a second visit would otherwise risk the bridge reading the refused result.

## Risks / Trade-offs

- [A refusal the agent can't fix, such as a rule it disagrees with] → three visits, then the run fails as today; the bridge's message is unchanged.
- [Each extra visit is a new Claude Code session that re-reads the issue] → a few minutes and some Max usage, only on runs that would otherwise have failed.
- [Fabro's routing differs from its docs] → the live check (task 4.2) proves the loop on a real run before it's relied on, and a new test runs `fabro validate` on both graphs when `fabro` is installed, as `test_issue_builds.py` does for the build graph.
- [The bridge fix ships late] → task order: intentable first.
- [Fabro's circuit breaker] also ends a run when the same failure repeats three times; three identical refusals trip it at the same point `max_visits` would, so the behaviour is the same, but a later change to `max_visits` must allow for it.
- ["Results the bridge would refuse fail the run" keeps its name] → its body, the checker exiting with a failure, still holds; only the run's ending changes, which "A run ends with its result" now says.

## Migration Plan

1. Merge and deploy intentable's `latestResult` fix.
2. Merge this change to the fork's `main`. The bridge reads workflows from `main`, so the next triage or clarify run uses the loop.
3. Rollback: revert the merge on the fork's `main`; the bridge fix is harmless on its own.
