You are building a confirmed change to the New England Music Project website, a Django app that lists music venues, shows and acts in the Northeast US. The repository is checked out in your working directory on the change's branch, and the `openspec` command is installed.

## The change

- Change: `{{ inputs.change_name }}`, in `openspec/changes/{{ inputs.change_name }}/`
- Issue: #{{ inputs.issue_number }}, "{{ inputs.issue_title }}"
- Picked design: `{{ inputs.picked_design }}` (empty when the change has no sketches to pick from)

When the picked design isn't empty, build the screens from `sketches/{{ inputs.picked_design }}.html` in the change's folder, and treat the other sketches as rejected. If that sketch is missing from the branch, stop as "When to stop" says, with the outcome `stopped`, and say which sketch is missing.

Nate confirmed this proposal at gate G2. The proposal, design, specs and tasks in the change's folder are your whole instruction: build what they say, no more and no less. Follow `AGENTS.md`, especially "Specs and tests (OpenSpec)" and "Code style". Keep host and network names out of everything you write.

## How to build it

Work through the change's `tasks.md` one `## N.` group at a time, in order. For each group:

1. Read the group's tasks and the parts of the proposal, design and specs they rely on, and the code they touch.
2. Make the group's changes, with the automated tests its tasks ask for.
3. Tick the box of each task you did, and only those.
4. Run the whole suite: `set -a; . ./.intentable/test.env; set +a; venv/bin/python manage.py test`.
5. Only when the suite passes, commit the group's work and its ticks together, as one commit. The subject says what the group did, in the repository's style (a short plain sentence, such as "Add the venue export to the admin"), and the body says why when that isn't obvious.

Never commit on a failing suite. One group is one commit: don't split a group, and don't fold two together.

## Tasks only a person can do

A task that only a person can do is left unticked: a check by hand in a browser, or a live check against an outside system. Nothing else counts as one. Do every other task in its group, commit the group as above, and list the task in your record (below) with the reason. Name each such task on one line in your message too, and give the full reasons in the summary.

## When to stop

If a group can't be made to pass, stop. Commit nothing for that group, and discard its changes so the working tree is clean: `git restore --staged --worktree .` and `git clean -fd` (ignored files stay). Record the outcome `stopped`, and say in plain words which group you reached and why it couldn't pass.

If the proposal leaves a decision open that you can't build without, don't guess, and never ask and wait for an answer: nobody is waiting on this run. Stop the same way, and put the question in your message. The answer will come through the change's own artifacts: Nate writes it into the change's design on its branch, then starts the build again.

## Never

- make a merge commit, or pull, rebase or push: the run's branch is pushed for you;
- write a closing keyword followed by an issue reference in a commit message, such as "fixes #3", "closes: #3" or "resolves owner/repo#3";
- change anything under `.github/` or `.fabro/`, or `bin/publish-spek-page`;
- put an `@` in your message for the issue, except inside backticks for code, such as `` `@admin.register` ``;
- start subagents or background tasks;
- commit `.claude/settings.local.json`, your session's own settings: stage files by name, never with `git add -A` or `git add .`;
- leave anything uncommitted: end every group, and the whole session, with a clean working tree (`git status --porcelain` lists nothing).

## Your record

When you stop or finish, write `.intentable/build.json`, creating the folder if needed:

```json
{"change": "{{ inputs.change_name }}", "outcome": "complete", "message": "The venue list now has an Export to CSV button for editors. One check is left for Nate: task 3.2, opening the file in Excel.", "left_for_people": [{"task": "3.2", "reason": "opening the downloaded file in Excel needs a person"}]}
```

- `outcome` is `complete` when every group is committed, or `stopped`.
- `message` is for the person who asked, who is not a developer: two to four plain sentences on what was built, or where and why you stopped, at most 2000 characters.
- `left_for_people` lists the tasks only a person can do, or is empty.

Then write `.intentable/summary.md`, for the pull request Nate reviews: what changed and where, the tests added, and anything surprising. Leave out the tasks left for a person: a later step adds them from your record.

Write nothing else under `.intentable/`. A later step checks your commits and your record, and the run fails if they break these rules. Your session ends when you stop, and anything still running is lost, so stop only once the record and the summary are written and the working tree is clean.
