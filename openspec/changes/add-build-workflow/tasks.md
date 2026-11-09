## 1. Settings and setup

- [ ] 1.1 Add `.fabro/workflows/build/workflow.toml`:
  - the six inputs with empty defaults;
  - `[run.run_branch] push = true` and `[run.pull_request] enabled = false`;
  - artifacts `.intentable/result.json` and `.intentable/pull-request.md`;
  - comments saying who starts it and why it pushes.
- [ ] 1.2 Add `workflow.fabro` with `on_failure="exit"` and its setup command:
  - the pinned tools;
  - `uv`, Python 3.11, `venv/` and `requirements-dev.txt`;
  - Postgres started, with a `djtesting` database, as root or with `sudo`;
  - `playwright install --with-deps chromium` and `compilescss`;
  - `.intentable/test.env` with CI's test environment;
  - `.intentable/start`;
  - a final `git status --porcelain` check that fails on any change.
- [ ] 1.3 Add `core/tests/test_issue_builds.py`, with tests for "Declared inputs", "Build settings", "The other workflows still push nothing", "Setup's tools", "Setup checks the tree", "Commands without inputs" and "No script from the checkout". Verify `venv/bin/python manage.py test core.tests.test_issue_builds core.tests.test_fabro_config` passes.

## 2. The agents

- [ ] 2.1 Write `apply.md`:
  - the issue and `{{ inputs.change_name }}`;
  - reading the change's artifacts;
  - one group at a time, with ticks in the same commit, never on red, and the suite run with `.intentable/test.env`;
  - stopping and discarding a group that can't pass;
  - the forbidden list and the clean tree;
  - the record `.intentable/build.json` (`change`, `outcome`, `message`) and `.intentable/pull-request.md`;
  - finishing its own work, with no subagents.
- [ ] 2.2 Write `refactor.md`, with intentable's refactoring rules condensed into it: at most one commit, only on green, no change to specified behaviour, the same forbidden list, a clean tree, and a line it may add to the summary
- [ ] 2.3 Add the apply and refactor nodes to the graph as ACP agents (`claude-agent-acp`), and verify with tests for "The apply prompt names the change", "ACP agents only", "The apply prompt states the commit rule", "The apply prompt says when to stop", "The forbidden list", "The prompts say to leave a clean tree", "The refactor prompt states the rules" and "The refactoring rules travel with the workflow"

## 3. Route and finish

- [ ] 3.1 Add the route node: inline Python that reads `.intentable/build.json` and prints the routing update, `refactor` for `complete` and `finish` otherwise. Add the edges route → refactor → finish and route → finish.
- [ ] 3.2 Add the finish node: inline Python, single-quoted only. It reads the record and checks the change's folder, then checks the commits from `.intentable/start` to `HEAD`:
  - merges, `fabro(` checkpoint subjects and closing keywords;
  - protected paths, renames included.

  For a complete build it also checks `tasks.md` and that there is at least one commit. It then runs the suite (the command replaceable through one environment variable), checks the message (non-empty, no mention, at most 2000 characters), and writes `result.json` and `pull-request.md`. Each failure gets one plain reason, naming the commit, path or task. A comment beside the closing-keyword pattern names the bridge's copy.
- [ ] 3.3 In the tests, extract the route and finish scripts from `workflow.fabro` and run them in temporary git repositories, with the suite command set to `true` or `false`. Verify with tests for "Routing on the outcome", "A clean complete build", "A merge commit", "Work left uncommitted", "A closing keyword" (with the colon, cross-repository, address and several-reference forms), "A protected file", "An unticked box", "A stopped build with an unfinished group", "A failing suite", "A malformed record", "The written result", "A message that mentions someone" and "The build graph".
- [ ] 3.4 Add a test for "The graph is valid" that runs `fabro validate` on the build graph, skipped when `fabro` isn't installed (as in CI). Run it locally and record that it passed.

## 4. Guide

- [ ] 4.1 Add a build workflow section to `docs/FABRO.md` covering:
  - what starts it (the bridge, after `/approve`);
  - its inputs and target;
  - its steps, the commit rules, and what finish checks;
  - what it leaves for the bridge, and that a stopped build is only reported;
  - how to test it from a branch with `FABRO_WORKFLOW_REF`.

  Verify with a test for "Guide section".

## 5. Live check (with intentable's `add-build-runs`)

- [ ] 5.1 After Nate's G2 and once groups 1–4 are green, push `change/add-build-workflow` to the fork. Verify with `gh api repos/natea/newenglandmusic/contents/.fabro/workflows/build?ref=change/add-build-workflow` that the folder is there.
- [ ] 5.2 With Nate's go-ahead and intentable's task 8.3 done, deploy the bridge with `FABRO_WORKFLOW_REF=change/add-build-workflow`. Nate comments `/approve` on issue #14.
- [ ] 5.3 From the run, record in `design.md`:
  - whether setup ran as root or with `sudo`, and how long it took;
  - whether the inline scripts ran as written;
  - whether Fabro added checkpoint commits;
  - the run branch's commits, and the result and summary.

  Fix the design and code if the run contradicts them.

## Workflow follow-up

- Merge to `main` at Nate's G4, then remove the bridge's `FABRO_WORKFLOW_REF`.
- Archive after the live check, once every scenario has a passing test.
