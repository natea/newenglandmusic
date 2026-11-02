## 1. The result checker

- [x] 1.1 Add `bin/check-intentable-result <triage|clarify> [path]`. It is Python with no dependencies, reads `.intentable/result.json` by default, holds the bridge's issue labels and states (citing `bridge/src/labels.ts` in natea/intentable), and exits non-zero with a plain reason. Add `core/tests/test_issue_triage.py` with tests for "No result file", "A label the bridge doesn't know" and "Not JSON", and a change-detector test that pins the label list.
- [x] 1.2 Check the triage rules (exactly one type, clarity, risk, blast and size label; `spec-review`, `needs-info` or `parked`) and refuse later-stage labels. Add tests for "A complete triage result", "A triage result missing a group", "Two labels of one group" and "A label for a later stage".
- [x] 1.3 Check the clarify rules (exactly one clarity label, at most one each of type, risk, blast and size; `spec-review` or `needs-info`). Add tests for "Clarify asks again" and "Clarify can't park".
- [x] 1.4 Check the clarity rule and the message:
  - clarity 4–5 ↔ `spec-review`, 1–3 ↔ `needs-info`, `parked` any;
  - a message is always there;
  - a `needs-info` message has exactly one `?`;
  - no `@login` at the start of a word (an email address passes);
  - at most 2,000 characters.

  Add tests for "Unclear but written up", "Clear but asking", "Two questions at once", "No question", "No message", "A mention", "An email address" and "Too long", each on an otherwise complete result. Verify the suite passes.

## 2. The workflows

- [x] 2.1 Add `.fabro/workflows/triage/`:
  - `workflow.toml`: the five inputs with `""` defaults, pull requests and run-branch pushing off, `[run.artifacts] include = [".intentable/result.json"]`;
  - `workflow.fabro`: `on_failure="exit"`, `start → install → think → check → exit`. `install` runs `python3 --version`, then the pinned installs from `claude-max`. `think` is an ACP agent with `prompt="@prompt.md"`. `check` runs `python3 bin/check-intentable-result triage`;
  - `prompt.md`, with the rules in design.md. It names roles, not people, and never names the upstream repository.
- [x] 2.2 Add `.fabro/workflows/clarify/` the same way, with the clarify rules, and its check running `python3 bin/check-intentable-result clarify`.
- [x] 2.3 Add `.intentable/` to `.gitignore`. Add tests for:
  - "Workflow shape", "Inputs declared and used" and "Commands without inputs";
  - "Nothing pushed", "No human gate" and "Result collected, not committed";
  - "Prompt rules".

  Keep `test_fabro_config.py`'s test that no file under `.fabro/` names the upstream repository passing.

## 3. The guide

- [x] 3.1 Add sections to `docs/FABRO.md` for `triage` and `clarify`: what each does, which issues start them (through the intentable bridge), what the result looks like, and how to try one by hand, with `fabro run natea/newenglandmusic@<branch>:triage --environment daytona --target natea/newenglandmusic@<branch>` and the five inputs. Add a test for "Guide sections".
- [x] 3.2 Run the full suite (`python manage.py test`) and fix what this change broke
  - 2 November 2026: 1,479 tests, one failure, `test_youtube_preview_browser.test_click_opens_the_video` ("150 not greater than or equal to 200"). It fails the same way on `main` (503401b) without this change, so it isn't this change's; it came with other work on `main`. Everything this change adds passes.

## 4. Live check on the Spark

This needs the intentable change that makes `FABRO_WORKFLOW_REF` also set the run's target. One go-ahead from Nate covers the steps below. It touches GitHub: a pushed branch on the fork, comments and labels from the bridge on the issues named in 4.1, a reply on #9, then deleting the pushed branch.

- [x] 4.1 Push the change branch to natea/newenglandmusic, set `FABRO_WORKFLOW_REF` to it in the Spark's `bridge.env`, and restart the bridge.
  - First, list the open issues from intake users with no state label: #9 on 2 November, while the list is only `natea`. The restart's catch-up starts triage on each of them; agree that list with Nate at the time. An issue he leaves off gets a state label by hand before the restart, so catch-up skips it.
  - From then until 4.4, every intake user's issue or reply runs the change branch's workflows.
  - 2 November 2026: the open intake issues with no state were #9 only (intake list `natea`; Sooz's #5 and #6 are not on it). The bridge was updated on the Spark (test branch as target), `FABRO_WORKFLOW_REF=change/add-triage-clarify` set, and restarted. Fabro refused the run: "no LLM provider is ready, and the workflow has a node that runs a model". Fabro counts Anthropic as ready only with an `ANTHROPIC_API_KEY`; the subscription token isn't a provider credential. Nate chose to add an Anthropic API key to the Spark's Fabro vault. The sandbox still gets an empty `ANTHROPIC_API_KEY` from the `daytona` environment, so Claude Code runs on the Max subscription. The bridge posted "couldn't start" on #9 and rolled back its label, as specified.
- [x] 4.2 Watch the triage run that catch-up starts for #9. Check:
  - the issue gets five labels and a state;
  - the message is plain and asks one question, or summarises;
  - no question waits in Fabro;
  - how long the run took;
  - the run's sandbox is deleted.

  Record the run ID, labels, state, message and time here. No redelivery: catch-up already started it.
  - 2 November 2026: with the Anthropic key in the Spark's vault, a restart still started nothing, because Nate had added `state:triage` and `state:needs-info` to #9 by hand (thinking that would start a run; catch-up skips any issue with a state). With both labels removed and the bridge restarted, catch-up started run 01M6F1FFYE2HCWBRE465XCQ9FE. It succeeded in about 2 minutes. #9 got `type:feature`, `clarity:3`, `risk:2`, `blast:2`, `size:L` and `state:needs-info`, and one plain question with three options (booking basics only; basics plus capacity, sound system and pay norms; or a separate artist view), drawn from the venue fields in the code. No question waited in Fabro. The bridge gave the sandbox its three limits and deleted it when the run succeeded.
- [x] 4.3 If #9 went to `needs-info`, Nate replies on #9. Check that clarify runs, reads the thread, and either asks the next single question or moves #9 to `spec-review`. Record the run and result here.
  - 2 November 2026: Nate replied "c" (a separate artist view); clarify run 01M6F1T1H21MA6Z26PG7RJWNP3 summarised it and asked the next single question. His next reply (an alphabetical list filtered by town or genre, like the homepage) started clarify run 01M6F28HYW2N4VS6RSNAK0RJV3, which judged clarity 4 and moved #9 to `state:spec-review` with a summary, revising `risk:2` to `risk:1` and `size:L` to `size:M`. Both sandboxes were limited and deleted.
- [x] 4.4 Remove `FABRO_WORKFLOW_REF` from the Spark's `bridge.env`, restart the bridge, and delete the pushed change branch from the fork.
  - 2 November 2026: `FABRO_WORKFLOW_REF` removed and the bridge restarted; catch-up started nothing. The pushed branch was kept, not deleted: since this proposal was written, Nate's Spek rules (add-spek-pages) keep `change/` branches on the fork, with a standing go-ahead to push them, so their Spek pages keep working. The restart's catch-up finds #9 with a state, so it starts nothing. An intake issue still without a state would get "the agent couldn't start" until the change is merged, and so would a reply on #9 if it is still `needs-info`.

## Workflow follow-up

- After Nate's G4: archive the change, merge into `main`, then push `main` to natea/newenglandmusic with his go-ahead. That also deploys the site on Render.
- In natea/intentable:
  - the bridge's README says a change to its labels must also change `bin/check-intentable-result` here;
  - the README's workflow contract and the dictionary say "the last step that writes files" instead of "the last step", and "every file Fabro reads for the workflow" instead of "every file it refers to";
  - the prerequisite change that makes `FABRO_WORKFLOW_REF` set the run's target also corrects the README's "targeting the default branch".
- nycnoise has no dictionary of its own (engineering-practice E2): start `docs/dictionary.md`, or point to intentable's, in a change of its own.
