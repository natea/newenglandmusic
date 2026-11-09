## 1. Settings and setup

- [x] 1.1 Add `!/.fabro/workflows/build/` to `.gitignore` right after `build/`, and verify `git check-ignore .fabro/workflows/build/workflow.fabro` reports nothing
- [x] 1.2 Add `.fabro/workflows/build/workflow.toml`:
  - the six inputs with empty defaults;
  - `[run.run_branch] push = true` and `[run.pull_request] enabled = false`;
  - no GitHub permissions table;
  - artifacts `.intentable/result.json` and `.intentable/pull-request.md`;
  - comments saying who starts it and why it pushes.
- [x] 1.3 Add `workflow.fabro` with `on_failure="exit"` and its setup command, with a 30-minute `timeout`:
  - the pinned tools;
  - `uv`, Python 3.11, `venv/` and `requirements-dev.txt`;
  - Postgres started as root or with `sudo`, with a `djtesting` database, failing unless `server_version_num` is at least 140000;
  - `playwright install --with-deps chromium` and `compilescss`;
  - `.intentable/test.env` with CI's test environment, and `.intentable/start`;
  - a final `git status --porcelain` check that fails on any change.
- [x] 1.4 Add `core/tests/test_issue_builds.py`. Its step parser follows each quoted attribute to its closing quote, so a `]` inside a script doesn't cut it short. Verify with tests for "Nothing ignored", "Declared inputs", "Build settings", "The other workflows still push nothing", "Setup's tools", "Commands without inputs" and "No script from the checkout", and that `venv/bin/python manage.py test core.tests.test_issue_builds core.tests.test_fabro_config` passes.

## 2. The agents

- [x] 2.1 Write `apply.md`:
  - `{{ inputs.change_name }}`, the issue's number and title, and no body or thread;
  - reading the change's artifacts;
  - one group at a time, ticks in the same commit, never on red, with the suite run through `.intentable/test.env`, and a subject in the repository's style;
  - tasks only a person can do (a check by hand in a browser, or a live check against an outside system), left unticked, listed in `left_for_people` and named in the message in one line each, with the full reasons in the summary, so the message stays under 2000 characters;
  - stopping, and discarding a group that can't pass;
  - never asking and waiting, but stopping with the question in the message, whose answer will arrive in the change's artifacts;
  - the forbidden list, the clean tree, and code names in backticks;
  - the record `.intentable/build.json` (`change`, `outcome`, `message`, `left_for_people`) and the summary `.intentable/summary.md`;
  - finishing its own work, with no subagents.
- [x] 2.2 Write `refactor.md`:
  - `{{ inputs.change_name }}`;
  - the condensed rules R1–R5, R7 and R11;
  - R6, R9 and R10 findings reported in the summary, never acted on;
  - at most one commit, "Refactor <change>", only on green;
  - the same forbidden list, the clean tree, and never asking and waiting.
- [x] 2.3 Add the apply and refactor nodes to the graph as ACP agents (`claude-agent-acp`). Verify with tests for:
  - "The prompts name the change, not the thread", "ACP agents only", "The apply prompt states the commit rule", "The apply prompt says what to leave" and "The apply prompt says when to stop";
  - "No question asked", "The forbidden list", "The prompts say to leave a clean tree" and "The refactor prompt states the rules".

## 3. Route and finish

- [x] 3.1 Add the route node: inline Python, with no double quotes, backslashes or `{{`. It reads `.intentable/build.json` and prints the routing update: `refactor` for `complete`, `finish` otherwise. Add the edges route → refactor → finish and route → finish.
- [x] 3.2 Add the finish node: inline Python, with no double quotes, backslashes or `{{`, and a 60-minute `timeout`. It:
  - reads the record, and checks the outcome, the change's folder, the message rules (with a comment naming `bin/check-intentable-result` as their source; mentions inside backticks allowed) and `left_for_people`;
  - checks the commits from `.intentable/start` to `HEAD`: merges, checkpoint commits that change a file, closing keywords (with a comment naming the bridge's copy), and protected files, renames included;
  - for a complete build, checks there is at least one commit besides empty checkpoints, and that `tasks.md` has no unticked box outside `left_for_people`;
  - runs the suite (the command replaceable through one environment variable);
  - writes `result.json`, and `pull-request.md` whenever there is a summary or a task left for people;
  - ends by failing if `git status --porcelain` lists anything.

  Each failure gets one plain reason, naming the commit, path or task.
- [x] 3.3 In the tests, extract the route and finish scripts from `workflow.fabro` and run them in temporary git repositories, with the suite command set to `true` or `false`. Verify with tests for:
  - "Routing on the outcome", "The build graph", "Inline scripts without escapes" and "Setup and finish check the tree";
  - "A clean complete build" (with empty checkpoint commits), "A merge commit", "Work left uncommitted", "A closing keyword" (with the colon, cross-repository, address and several-reference forms) and "A protected file";
  - "An unticked box", "Nothing built", "A task left for a person", "A listed task that isn't left", "A stopped build with an unfinished group" and "A failing suite";
  - "A malformed record", "No record", "A message that breaks the rules" and "Code in the message";
  - "The written result" and "No summary".
- [x] 3.4 Add a test for "The graph is valid" that runs `fabro validate` on the build graph, skipped when `fabro` isn't installed (as in CI). Run it locally, and record that it passed in this task's note, for the archive check.
  - 9 November 2026: passed locally with fabro 0.400.0-nightly.0 (`manage.py test core.tests.test_issue_builds.BuildGraphTestCase.test_the_graph_is_valid`).

## 4. Guide

- [x] 4.1 Add a build workflow section to `docs/FABRO.md`, covering:
  - what starts it (the bridge, after `/approve`);
  - its inputs and target;
  - its steps;
  - the commit rules;
  - what finish refuses;
  - what it leaves for the bridge, and that a stopped build is only reported;
  - answering a stopped build's question: write the answer into the change's artifacts on its draft branch, reading it first if an agent wrote it, then run `retry-build.ts`, which works only while no build's work is on the branch;
  - testing from a branch with `FABRO_WORKFLOW_REF`.

  Any by-hand `fabro run` line names the fork and `--environment daytona`. Verify with a test for "Guide section".

## 5. Live check (with intentable's `add-build-runs`)

- [ ] 5.1 After Nate's G2 and once groups 1–4 are green, push `change/add-build-workflow` to the fork. Verify with `gh api 'repos/natea/newenglandmusic/contents/.fabro/workflows/build?ref=change/add-build-workflow'` that every file of the folder is there.
- [ ] 5.2 With Nate's go-ahead and intentable's task 8.3 done, deploy the bridge with `FABRO_WORKFLOW_REF=change/add-build-workflow`. Nate comments `/approve` on issue #14.
- [ ] 5.3 From the run, record in `design.md`, and fix the design and code if the run contradicts them:
  - root or `sudo`;
  - the setup, suite and agent times, and any agent timeout that applied;
  - whether checkpoint commits appeared, and whether they were empty;
  - whether the inline scripts ran as written. Before the live run, show it once with a test branch whose commit has "Fixes #1" and see finish refuse it;
  - the run branch's commits, the tasks left for people, and the result and summary.

## Workflow follow-up

- Merge to `main` at Nate's G4, then remove the bridge's `FABRO_WORKFLOW_REF`.
- Archive after the live check, once every scenario has a passing test. "The graph is valid" passes only where `fabro` is installed; note that at archive.
- In intentable's `add-build-runs`, reword live check 8.5 and the dictionary's `outcome` to match this change. `complete` means every group committed, apart from tasks left for a person, and the refactoring pass made, with any commit it made. `stopped` also covers a decision the proposal leaves open.
