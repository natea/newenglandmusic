## Why

On 9 November 2026, the clarify run for issue #24 asked a good question, but quoted the site's existing note "Is this you? Send us a photo, bio or links", so its message had two question marks. `bin/check-intentable-result` refused it, as the rules say, and that ended the run: the bridge posted "The agent stopped before finishing. Nate will look at it.", and the issue sat in `needs-info` with no question asked. One slip by the agent, which it could have fixed in seconds, needed Nate. On 9 November 2026 the author offered to send refusals back to the agent, up to two tries, in the triage and clarify workflows, and Nate agreed.

## What Changes

- **A refused result goes back to the agent.** In the `triage` and `clarify` workflows, when the check refuses the result, the run goes back to the agent step instead of ending. The agent reads why, fixes its result, and the check runs again. After three refusals in all, the run fails as it does today.
- **The check writes down why it refused.** When it refuses a triage or clarify result, `bin/check-intentable-result` also writes its one-line reason to `.intentable/refused.txt`, and removes that file when it accepts one. The folder is git-ignored and the file isn't collected, so nothing reaches the bridge but the result.
- **The prompts say what to do.** Each prompt tells the agent: if `.intentable/refused.txt` exists, a check refused your last result; fix what it names in `.intentable/result.json`, keep your decision unless the reason is about the decision itself, and change nothing else.
- **intentable's bridge reads the latest visit's result.** A second visit to the agent step writes its own `.intentable/result.json`, which Fabro keeps under the step's second visit (`think@2`) with a retry count that starts again at 1. The bridge picks a run's result by that retry count alone, so it could read the first, refused one. It must prefer the latest visit, then the latest retry. That is a small intentable change, `read-latest-visit-result`, which corrects its `run-status` spec and fixes `bridge/src/status.ts`, with a test. We ask that Nate's G2 here confirm it too, since it is small and its whole spec change is described in task 1.1. If he wants to see it first, it gets its own G2 before task 1.2.
- **Docs:** `docs/FABRO.md` describes the loop.

Out of scope:
- the `spec` workflow, whose draft check runs after a costly review, and the `build` workflow, whose finish step checks commits the agent can't easily undo; both keep ending the run on a refusal;
- loosening the one-question rule, for example allowing a question mark inside quotes: the rule stays as simple as the prompts teach it (the author's preference, which Nate didn't reopen);
- telling the issue that the agent is retrying: a retry takes a few minutes, and changes nothing anyone sees until the result is applied.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `issue-triage`: a refused result goes back to the agent, up to two more times, before the run fails; the check writes its reason down; the prompts say what to do with it.

## Impact

- `.fabro/workflows/triage/workflow.fabro` and `clarify/workflow.fabro`: an edge from the check back to the agent on failure, and a visit limit on the agent and check steps.
- `.fabro/workflows/triage/prompt.md` and `clarify/prompt.md`: the refusal section.
- `bin/check-intentable-result`: writing and removing `.intentable/refused.txt` for triage and clarify.
- `core/tests/test_issue_triage.py`: the workflow shape, the prompts and the checker's file.
- intentable's small change `read-latest-visit-result`: its `run-status` spec and `bridge/src/status.ts` (`latestResult`), with tests, deployed before this change reaches the fork's `main`.
- A refused run costs up to two more agent turns, each a fresh Claude Code session on the Max subscription.
