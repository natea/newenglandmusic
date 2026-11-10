## 1. intentable: read the latest visit's result

- [ ] 1.1 In intentable, a small OpenSpec change `read-latest-visit-result` on its own branch, confirmed by Nate's G2 on this change if he agrees to that, or by its own G2 before 1.2. It MODIFIES `run-status`' "The workflow result file", keeping every scenario: the result is written by one step, not necessarily the last, and "The bridge reads that step's highest retry" becomes "the latest visit of the step that wrote it, then its highest retry". It adds a scenario for a result written at `think@1` and again at `think@2`. Verify with `openspec validate read-latest-visit-result --strict` in intentable.
- [ ] 1.2 Build it: `latestResult` in `bridge/src/status.ts` sorts by the visit in `stage_id`, compared as a number, then by `retry`, both descending, with a comment that the bridge assumes one step writes the result. Verify with a test that lists `think@1` before `think@2`, both at retry 1, as Fabro returns them, and picks `think@2` (it fails on today's code); one with `think@2` and `think@10`; and one with a single entry picked as before. Then `bun test` and the type check.

## 2. The check

- [ ] 2.1 In `bin/check-intentable-result`, for triage and clarify only, write the reason, without the printed prefix, to `refused.txt` beside the result file when refusing, a missing result included, creating the folder if it isn't there, and remove it when accepting. Add a test with no `.intentable/` folder at all. Verify with tests for "A refusal", "A missing result after a refusal", "Accepted after a refusal", "Refused, then fixed" and "A spec draft" (using a refusing draft from the issue-proposals tests). The agent step running again is covered by the shape test in 3.1 and proven live in 4.2.

## 3. The workflows and prompts

- [ ] 3.1 Add `check -> think [condition="outcome=failed"]` to both graphs, and `max_visits=3` inside the existing `think [...]` and `check [...]` blocks, never as a second statement, which the tests' step parser would read as replacing the first. Unquoted, as the spec workflow writes it, so the "visit limit" test reads unquoted values. Verify with the updated "Workflow shape" test, a test for "The visit limit", the "No human gate" test unchanged, and a new test, skipped unless `fabro` is installed, that runs `fabro validate` on both graphs; run it locally.
- [ ] 3.2 Add the refusal section to the top of both prompts, as design.md words it. Verify with the updated "Prompt rules" test.
- [ ] 3.3 Describe the loop in `docs/FABRO.md`, replacing "A refused result fails the run", and name `.intentable/refused.txt` and the three visits. Where it gives the by-hand command, say the file lands beside the result checked. Verify with the updated "Guide sections" test.
- [ ] 3.4 Run the whole suite and verify it passes.

## 4. Live check

- [ ] 4.1 With Nate's go-ahead, merge and deploy group 1 in intentable, then merge this change to the fork's `main` and push it.
- [ ] 4.2 Check the next triage or clarify run that's refused once: its stages show `think@2`, the check passes on the second visit, and the bridge applies the second result to the issue. If none is refused within a few days, record that here and check it on the first that is.

## Workflow follow-up

- Archive after 4.2.
