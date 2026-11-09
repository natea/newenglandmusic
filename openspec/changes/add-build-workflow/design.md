## Context

The repository's workflows (`triage`, `clarify`, `spec`) run in the server's `daytona` environment, as Claude Code through ACP on the subscription token. Each one checks its result with `bin/check-intentable-result`, run from the checkout. All of them push nothing.

intentable's `add-build-runs` (built, confirmed by Nate on 9 November 2026) changes three things for builds:
- it starts `build` with the five issue inputs plus `change_name`;
- it targets the change's draft branch at the G2 commit, while reading the workflow from `main` or from the test branch in `FABRO_WORKFLOW_REF`;
- it publishes the run branch `fabro/run/<run-id>` only after its own checks, opening the pull request itself.

Its design's "contract with nycnoise's `add-build-workflow`" is the brief for this change.

Two Fabro facts shape the design:
- **The workflow's folder may not be in the sandbox.** A run's checkout is the target branch. Fabro resolves prompt files when it reads the workflow, but doesn't document putting the workflow's own folder into the sandbox, so a command can't rely on a script beside the graph.
- **Fabro commits after each step.** After every node that changed files, Fabro stages the changes and adds a checkpoint commit, `fabro(<run-id>): <node> (<status>)`, to the run branch, and pushes it.

## Goals / Non-Goals

**Goals:**
- Build a confirmed change exactly as the change cycle asks: one green commit per task group, ticks in the same commit, then a refactoring pass.
- Leave the bridge nothing it would refuse, and fail loudly in the sandbox when an agent broke a rule, rather than at the bridge.
- Work on any draft branch, however old.

**Non-Goals:**
- Judging the build's quality. That is Nate's G4, on the pull request.
- Serving a preview, which comes with the next change.
- Resuming a stopped build where it left off: a retry starts again from the draft branch.

## Decisions

**Graph: setup → apply → route → refactor → finish, or route → finish.** Apply is one agent for all groups, not one node per group. A change's group count isn't known when the graph is written, and Fabro's graphs are static. A single agent session also keeps what it learned in group 1 for group 2. Route is an inline command that reads apply's record and sends a `stopped` build straight to finish, so no refactoring pass runs on unfinished work.

Alternative: a looping node per group, with a counter in the context. That's more moving parts, and Fabro's loop limits (`max_visits`) would need a bound the change doesn't know.

**Checks inline in the graph.** The draft branch for #14 was cut before this change, so `bin/` on it has no build checker. The route and finish steps are command nodes with `language="python"` and the script written in `workflow.fabro`. `fabro validate` accepts a multi-line script; the live check confirms Fabro runs it as written. The tests extract that script text from the graph and run it in temporary git repositories, so they exercise the real check (rule E1), not a copy.

Alternatives:
- `git show origin/main:bin/check-intentable-build`: it fails for the test branch until merged, and ties a run to whatever `main` is at that moment.
- A server variable naming the ref: one more setting to keep right.

**Agents write a record; finish writes the result.** As with `spec`'s `draft.json`:
- **the apply agent** writes `.intentable/build.json`, with `change`, `outcome` and `message`, and `.intentable/pull-request.md`;
- **the refactor agent** may add a line to the summary;
- **finish, and only finish,** writes `.intentable/result.json`.

So a run that fails a check leaves no result the bridge could read as a build. `.intentable/` is git-ignored, so none of these reach a commit.

**The change's name reaches the agents only through their prompts.** The bridge's workflow contract keeps inputs out of commands. `change_name` is checked by the bridge, but a command still never sees it. Finish takes the change from the agent's record and checks that its folder exists; the bridge compares it with the G2.

**Setup, as CI does, in one command.**
- **Tools:** Claude Code, the ACP adapter and `openspec` pinned with `npm -g --prefix /usr/local`, as `spec` does.
- **Python:** `uv` installs Python 3.11 and creates `venv/`. `uv pip install -r requirements-dev.txt`, per `AGENTS.md`.
- **Postgres:** the distribution's Postgres package, started locally, with a `djtesting` database. Root or `sudo` is used as available.
- **Browser:** `playwright install --with-deps chromium`.
- **CSS:** `compilescss`.
- **Test settings:** CI's environment goes in `.intentable/test.env`: `DATABASE_URL`, `DJANGO_SETTINGS_MODULE=nycnoise.settings.test`, the dummy secret and the switches. Every test run sources it.
- **The start commit:** `git rev-parse HEAD` goes in `.intentable/start`, the base of finish's commit checks. This is the commit the run targeted: the G2 commit, or the head a retry chose.
- **A clean tree:** setup ends by failing if `git status --porcelain` lists anything, so its own checkpoint is empty. `venv/`, the compiled CSS and `.intentable/` are already ignored.

**The commit rules, in the prompts and in finish.** Apply works group by group:
1. read the proposal, design, specs and the group's tasks;
2. change the code and tests;
3. tick the group's boxes;
4. run the suite;
5. commit only if it passes, with a message saying what the group did.

If a group can't pass, the agent stops, discards that group's changes (`git restore`, `git clean` of untracked files outside ignored paths), records `stopped` and says why in plain words. Both prompts forbid:
- merges and pushes;
- closing keywords in messages;
- `.github/`, `.fabro/` and `bin/publish-spek-page`;
- subagents and background tasks;
- leaving anything uncommitted.

Finish then checks the commits between `.intentable/start` and `HEAD`. Each check reads git directly: `git rev-list --parents` for merges, and `git diff-tree -r -M --name-status` for files, renames included. A checkpoint subject `fabro(` means an agent left work behind, so the run fails. The closing-keyword pattern matches the bridge's: any case, an optional colon, `#N`, `owner/repo#N`, an issue address, and several references after one keyword. A comment beside it says the bridge's copy, in intentable's `bridge/src/builds.ts`, must change with it.

**Refactoring rules travel in the prompt.** The fork has no `_workflows/`, and the draft branch couldn't be relied on to have it anyway. So `refactor.md` states the rules it applies, condensed from intentable's `_workflows/refactoring.md`: smaller units with clear names, no duplicated logic, the project's vocabulary, no change to specified behaviour, the suite green before and after. It makes at most one commit, "Refactor <change>", or none.

**Finish runs the suite once more,** with the same environment. A build that is green at each group but red at the end, after the refactor, fails the run instead of being published. The command finish runs is `venv/bin/python manage.py test`, which the tests replace through one environment variable, so they never run the suite recursively.

**Mocks in tests.** The configuration tests read files only. The finish and route tests build small git repositories in temporary folders, with the suite command replaced by `true` or `false`. No Fabro, GitHub, Anthropic or Daytona is reached, and no outside service is called. That follows the repository's rule that tests never touch the network.

## Risks / Trade-offs

- **[Root in the sandbox]** Installing Postgres and Chromium's system libraries needs root or `sudo`. → `spec`'s install writing to `/usr/local` suggests one of them works. Setup uses whichever is there, and fails clearly otherwise. The live check confirms it.
- **[Long setup]** Python, the requirements, Postgres and Chromium add minutes to every build. → Accepted for now. A prebuilt Daytona image (the plan's step 2) would remove most of it.
- **[The suite per group]** Running the whole suite after every group is slow on a large change. → It is what G3 asks. The 360-minute lifetime and a test-per-group budget in the prompt bound it.
- **[A checkpoint commit with work in it]** If an agent ignores the clean-tree rule, Fabro still commits and pushes that work to the run branch before finish can refuse it. → Finish fails the run, so the bridge never publishes it. The run branch keeps it for Nate to look at.
- **[The two closing-keyword patterns]** The one in finish and the bridge's can drift. → A comment in each names the other. The bridge's check is the one that guards publishing.
- **[Inline scripts are harder to read]** Python inside a DOT attribute uses single quotes only and can't import a local module. → Each script stays short, and the tests run it as written.

## Migration Plan

1. Push `change/add-build-workflow` with the draft, for its Spek page, before G2.
2. After G2 and apply, test it from the branch: deploy the bridge with `FABRO_WORKFLOW_REF=change/add-build-workflow`. The branch carries `main`'s other workflows, since it is cut from `main`. Nate then comments `/approve` on issue #14, as intentable's `add-build-runs` task 8.4 describes.
3. Record what the live run showed: root or `sudo`, setup time, whether checkpoint commits appeared, and whether the inline scripts ran as written. Fix the design if they contradict it.
4. Merge to `main` at Nate's G4, then remove the bridge's test setting.

Rollback: removing `.fabro/workflows/build/` from the branch the bridge reads makes build starts fail, which the bridge reports; nothing else depends on it.
