## Context

The repository's workflows (`triage`, `clarify`, `spec`) run in the server's `daytona` environment, as Claude Code through ACP on the subscription token. Each one checks its result with `bin/check-intentable-result`, run from the checkout. All of them push nothing.

intentable's `add-build-runs` (built, confirmed by Nate on 9 November 2026) changes three things for builds:
- it starts `build` with the five issue inputs plus `change_name`;
- it targets the change's draft branch at the G2 commit, while reading the workflow from `main` or from the test branch in `FABRO_WORKFLOW_REF`;
- it publishes the run branch `fabro/run/<run-id>` only after its own checks, opening the pull request itself.

Its design's "contract with nycnoise's `add-build-workflow`" is the brief for this change.

Three facts shape the design:
- **The workflow's folder may not be in the sandbox.** A run's checkout is the target branch. Fabro resolves prompt files when it reads the workflow, but doesn't document putting the workflow's own folder into the sandbox, so a command can't rely on a script beside the graph.
- **Fabro commits after each step.** After every node, Fabro stages any changes and adds a checkpoint commit, `fabro(<run-id>): <node> (<status>)`, to the run branch, and pushes it. Its binary commits with `--allow-empty`, so steps that changed nothing very likely leave empty checkpoint commits too.
- **`.gitignore` ignores `build/` at any depth** (line 11, a Python packaging entry), which would silently keep `.fabro/workflows/build/` out of every commit.

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

**Keep the folder out of `.gitignore`.** A line `!/.fabro/workflows/build/` goes right after `build/`. A test asks `git check-ignore` about every file in the folder. Without it, the branch would be pushed without the workflow, and the bridge's first start would fail and use up #14's only build attempt. Anchoring the packaging line as `/build/` would also work, but would change what it ignores elsewhere.

**Graph: setup → apply → route → refactor → finish, or route → finish.** Apply is one agent for all groups, not one node per group. A change's group count isn't known when the graph is written, and Fabro's graphs are static. A single agent session also keeps what it learned in group 1 for group 2. Route is an inline command that reads apply's record and sends a `stopped` build straight to finish, so no refactoring pass runs on unfinished work.

Alternative: a looping node per group, with a counter in the context. That's more moving parts, and Fabro's loop limits (`max_visits`) would need a bound the change doesn't know.

**Checks inline in the graph.** The draft branch for #14 was cut before this change, so `bin/` on it has no build checker. The route and finish steps are command nodes with `language="python"` and the script written in `workflow.fabro`. `fabro validate` accepts a multi-line script. The scripts:
- use no double quotes and no backslashes, so nothing depends on how Fabro decodes the graph's strings. Patterns use character classes such as `[0-9]` and `[ ]`, with a literal tab where one is needed, and lookarounds instead of word-boundary escapes;
- contain no `{{`, since scripts are templated.

The tests extract the script text from the graph and run it in temporary git repositories, so they exercise the real check (rule E1), not a copy. Their step parser follows a quoted attribute to its closing quote, unlike the one in `test_fabro_config.py`, which a `]` inside a script would cut short. The live check also records a known-bad commit being refused, to show the scripts run as written.

Alternatives:
- `git show origin/main:bin/check-intentable-build`: it fails for the test branch until merged, and ties a run to whatever `main` is at that moment.
- A server variable naming the ref: one more setting to keep right.

**Agents write a record; finish writes the result.** As with `spec`'s `draft.json`:
- **the apply agent** writes `.intentable/build.json`, with `change`, `outcome`, `message` and `left_for_people` (each task it left for a person, with the reason, also named in its message). It also writes the summary, `.intentable/summary.md`;
- **the refactor agent** may add its findings to the summary;
- **finish, and only finish,** writes `.intentable/result.json`, and copies the summary to `.intentable/pull-request.md`, adding the tasks left for people.

So both files the bridge reads come from the last stage, as it expects. A run that fails a check leaves no result the bridge could read as a build. `pull-request.md` is written whenever there is a summary or a task left for a person, and left out otherwise, since the bridge opens the pull request without one. `.intentable/` is git-ignored.

**The agents see the change, not the thread.** The bridge sends all six inputs, and the workflow declares them. But the prompts use only `change_name`, `issue_number` and `issue_title`. The confirmed proposal is the instruction. The body and thread are text nobody reviewed, and the apply agent holds a token that can push. Commands get no input at all, per the bridge's workflow contract. Finish takes the change from the agent's record and checks that its folder exists; the bridge compares it with the G2.

**Setup, as CI does, in one command with a 30-minute timeout.** Fabro's default is ten minutes per command.
- **Tools:** Claude Code, the ACP adapter and `openspec` pinned with `npm -g --prefix /usr/local`, as `spec` does.
- **Python:** `uv` installs Python 3.11 and creates `venv/`. `uv pip install -r requirements-dev.txt`, per `AGENTS.md`.
- **Postgres:** the distribution's Postgres package, started locally, with a `djtesting` database. Root or `sudo` is used as available. Setup then checks `server_version_num` is at least 140000, since Django 5.2 needs PostgreSQL 14 (CI uses 17).
- **Browser:** `playwright install --with-deps chromium`.
- **CSS:** `compilescss`.
- **Test settings:** CI's environment goes in `.intentable/test.env`: `DATABASE_URL`, `DJANGO_SETTINGS_MODULE=nycnoise.settings.test`, the dummy secret and the switches. Every test run sources it.
- **The target commit:** `git rev-parse HEAD` goes in `.intentable/start`, the base of finish's commit checks. This is the commit the run targeted: the G2 commit, or the head a retry chose.
- **A clean tree:** setup ends by failing if `git status --porcelain` lists anything. `venv/`, the compiled CSS and `.intentable/` are already ignored.

**The commit rules, in the prompts and in finish.** Apply works group by group:
1. read the proposal, design, specs and the group's tasks;
2. change the code and tests;
3. tick the boxes of the tasks it did;
4. run the suite;
5. commit only if it passes. The subject says what the group did, and the body says why if it isn't obvious (G6).

**When apply stops, or leaves a task.**
- **A task only a person can do** is left unticked and listed in `left_for_people` with the reason. Only two kinds qualify: a check by hand in a local browser, or a live check against an outside system. Nate sees each one in the pull request and in the message for the issue. #14's tasks have one, a by-hand check that the export button downloads a file.

  This departs from G3's "every checkbox in the group is ticked" and from the contract's "one per task group, with its boxes ticked", and so from intentable's `complete` ("every task group … committed"). It is the author's decision, for Nate at G2. The reason is G3's own clause for a group whose check can't run where it is applied: "the gate is that group's own verifiable outcome instead". The group is committed once its automated tests pass, and the box stays honest, unticked for the person who will do it. The alternatives, ticking a box for work not done, or stopping every change that has a by-hand check, are worse. A Workflow follow-up rewords intentable's `outcome` to match.
- **A group that can't pass:** the agent stops, discards that group's changes (`git restore` and `git clean` of untracked files outside ignored paths), records `stopped` and says why in plain words.
- **A decision the proposal doesn't settle** gets the same treatment: the agent records `stopped`, with the question in its message.

**No build waits for a person.** This follows Nate's rule for this repository's runs: "Runs end with their result; no human gates. Nobody's answer is waited for" (2 November 2026, `add-triage-clarify`). intentable's bridge would relay a build's question to the issue. But a sandbox idles out after about 90 minutes waiting, and loses unpushed work, so a stopped build with the question in its message is the safer form.

**How the answer reaches a retry.** The agents never read the thread, so an answer posted on the issue would never reach a retried build. Instead, once Mark or Sooz answers on the issue, Nate writes the answer into the change's design (or proposal) on `change/<name>`, as a commit after G2, or has an agent do it. Then he runs `retry-build.ts`. The bridge's retry builds from the branch's head, as long as it holds the G2 commit, and checks every commit after G2. So the retried agent reads the answer as part of the proposal it applies. The apply prompt tells the agent that a question's answer will arrive that way, and the guide tells Nate.

This edits a confirmed proposal after G2, without a second `/approve`. That is Nate's own act, as the bridge's design treats any push he makes after G2. If an agent writes the commit for him, he reads it before retrying. The retry works only while no build's work is on the branch, which holds after a stopped build, since a stopped build is never published.

**What both prompts forbid:**
- merges and pushes;
- closing keywords in messages;
- the protected files (`.github/`, `.fabro/`, `bin/publish-spek-page`);
- an `@` in the message for the issue. Code names go in backticks;
- subagents and background tasks;
- leaving anything uncommitted.

**Finish's checks** run, with a 60-minute timeout, on the commits from `.intentable/start` to `HEAD`. Each check reads git directly: `git rev-list --parents` for merges, and `git diff-tree -r -M --name-status` for files, renames included. A Fabro checkpoint commit (subject starting `fabro(`) fails the run only if it changes a file. An empty one passes, and doesn't count as the build's work for the "at least one commit" rule.

The closing-keyword pattern matches the bridge's: any case, an optional colon, `#N`, `owner/repo#N`, an issue address, and several references after one keyword. A comment beside it says the bridge's copy, in intentable's `bridge/src/builds.ts`, must change with it.

The message rules are those of `bin/check-intentable-result` (not empty, at most 2000 characters, no `@` mention), plus one relaxation: a mention inside backticks is allowed, since GitHub notifies no one from code, so `` `@admin.register` `` passes. A comment names the source. The bridge posts the message as it is.

With no backslashes, line breaks and tabs come from `chr(10)` and `chr(9)`. The closing-keyword whitespace class is built from them at runtime, so "Fixes" followed by a line break and "#3" is caught, as the bridge's `\s` catches it. Git output is split with `splitlines()`.

Finish then runs the suite once more, with the same environment, and ends by failing if `git status --porcelain` lists anything, so its own checkpoint is empty. A build that is green at each group but red at the end, after the refactor, fails the run instead of being published. The suite command is `venv/bin/python manage.py test`, which the tests replace through one environment variable, so they never run the suite recursively.

**Refactoring rules travel in the prompt.** The fork has no `_workflows/`, and the draft branch couldn't be relied on to have it anyway. `refactor.md` carries intentable's `_workflows/refactoring.md`, condensed to what an unattended agent may act on:
- R1: no change in behaviour;
- R2: the suite passes afterwards, and the failure set doesn't grow;
- R3: renames go through the whole project;
- R4: break up long functions;
- R5: extract logic expressed more than once;
- R7: correct comments;
- R11: names say what things are.

What the rules leave to the owner is reported, not done, in the summary for Nate at G4:
- R6: circular dependencies and layering violations;
- R9: dead code, which needs the owner's confirmation;
- R10: a new grouping, or a move across a module or layer boundary.

**Refactor may make no commit.** It makes at most one commit, "Refactor <change>", or none when nothing is worth changing, as `dev-finish-change`'s refactoring step allows ("one commit, or none"). This narrows the wording of the contract Nate confirmed ("a refactoring pass as its own commit") and of intentable's `outcome` ("the refactoring pass were committed"). A `complete` build means the pass was made, with its commit optional. The bridge checks for no refactoring commit, so nothing breaks. Its live check 8.5 and its dictionary entry should say "the refactoring pass, with any commit it made". That is a wording fix for `add-build-runs` (Workflow follow-up).

**Mocks in tests.** The configuration tests read files only. The finish and route tests build small git repositories in temporary folders, with the suite command replaced by `true` or `false`. No Fabro, GitHub, Anthropic or Daytona is reached, and no outside service is called. That follows the repository's rule that tests never touch the network.

## Risks / Trade-offs

- **[Root in the sandbox]** Installing Postgres and Chromium's system libraries needs root or `sudo`. → `spec`'s install writing to `/usr/local` suggests one of them works. Setup uses whichever is there, and fails clearly otherwise. The live check confirms it.
- **[Long setup]** Python, the requirements, Postgres and Chromium add minutes to every build, on a 2-CPU sandbox. → Setup's timeout is 30 minutes. A prebuilt Daytona image (the plan's step 2) would remove most of it. The live check records the time.
- **[The suite per group]** Running the whole suite after every group is slow on a large change (about 1,500 tests today). → It is what G3 asks. The 360-minute lifetime bounds it, and the live check records the time. Fabro documents no default timeout for agent steps, and the live check notes whether one applied.
- **[A red suite before any group]** If the suite already fails on the draft branch, apply stops at group 1, and finish fails the run on the red suite. The issue then gets the bridge's failed-run comment, not the agent's reason. → Rare, since `main` is green in CI. Nate sees the agent's reason in the run.
- **[A checkpoint commit with work in it]** If an agent ignores the clean-tree rule, Fabro still commits and pushes that work to the run branch before finish can refuse it. → Finish fails the run, so the bridge never publishes it. The run branch keeps it for Nate to look at.
- **[The two closing-keyword patterns]** The one in finish and the bridge's can drift. → A comment in each names the other. The bridge's check is the one that guards publishing.
- **[The sandbox's token acts as Nate]** The run branch is pushed with the vault token, which can push any branch, `main` included. → `main` is protected against force-push and deletion before the live check. Blocking direct pushes waits for the Intentable GitHub App, which gives Fabro an identity of its own (Nate's decision, 9 November 2026).
- **[Inline scripts are harder to read]** Python inside a DOT attribute uses single quotes only, no backslashes, and can't import a local module. → Each script stays short, and the tests run it as written.

## Migration Plan

1. Push `change/add-build-workflow` with the draft, for its Spek page, before G2. Done.
2. After G2 and apply, push it again. Check the fork has `.fabro/workflows/build/` on the branch. Test it from the branch: deploy the bridge with `FABRO_WORKFLOW_REF=change/add-build-workflow`. The branch carries `main`'s other workflows, since it is cut from `main`. Nate then comments `/approve` on issue #14, as intentable's `add-build-runs` task 8.4 describes.
3. Record what the live run showed, and fix the design if it contradicts it:
   - root or `sudo`;
   - the setup, suite and agent times;
   - whether checkpoint commits appeared, and whether they were empty;
   - whether the inline scripts ran as written.
4. Merge to `main` at Nate's G4, then remove the bridge's test setting.

Rollback: removing `.fabro/workflows/build/` from the branch the bridge reads makes build starts fail, which the bridge reports; nothing else depends on it.

## Live check (9 November 2026)

Nate commented `/approve` on issue #14, with the bridge deployed from intentable's `change/add-build-runs` and reading workflows from `change/add-build-workflow`. Run `01M7158HF3VCMA82D8XCMZYQAP` took about 15 minutes from G2 to pull request #16:

| Step | Time | What it showed |
|---|---|---|
| Setup | about 3 minutes | root, Ubuntu 24.04, Postgres 16.15, Python 3.11.14 through `uv`. npm skipped Claude Code's postinstall script, as it does for `spec`, with no effect |
| Apply | about 8 minutes | four task-group commits with plain subjects. Task 3.1, which ends with a by-hand browser check, left unticked and listed for Nate |
| Route | | sent the complete build to refactor |
| Refactor | about 2 minutes | one commit, an import moved. It reported a module move for Nate instead of making it, and noticed the stray settings file below |
| Finish | about 1.5 minutes | the inline script ran as written, and the suite passed |

What the run settled:
- **Checkpoint commits.** Fabro adds a checkpoint commit after every step, empty or not (`fabro(<run-id>): <node> (success)`). There were eight, all empty, so passing empty checkpoints was right. They stay in the pull request's history.
- **Agent timeouts.** None applied.
- **The bridge's part.** It fast-forwarded `change/export-venues-csv` to the run branch, opened #16 (not a draft, with no closing keyword), and posted the agent's message with the link.

What it got wrong, fixed by task 5.4:
- **The agent's settings.** The first group's commit carried `.claude/settings.local.json`, the permissions the agent's Claude Code session saved, because the draft branch doesn't ignore it. It was removed from #16 by hand.
- **The tasks left for a person** appeared twice in #16's body, once from the agent's summary and once from finish.

