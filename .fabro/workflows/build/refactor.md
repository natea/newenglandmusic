You are making the refactoring pass on a change just built on the New England Music Project website, a Django app. The repository is checked out in your working directory on the change's branch, with each task group of the change already committed.

## The change

- Change: `{{ inputs.change_name }}`, in `openspec/changes/{{ inputs.change_name }}/`
- Issue: #{{ inputs.issue_number }}, "{{ inputs.issue_title }}"

Review the code this change added or touched, as `git diff $(cat .intentable/start)..HEAD` shows it, against the rules below. Follow `AGENTS.md`'s "Code style".

## What you may change

- **No change in behaviour.** Nothing a spec describes may change, and no test may change what it checks.
- **The suite passes afterwards, and no test that passed before fails.** Run it before and after: `set -a; . ./.intentable/test.env; set +a; venv/bin/python manage.py test`.
- **Renames go through the whole project:** code, tests, templates and the change's own artifacts.
- **Break up a long function** that does several non-trivial things into named steps.
- **Extract logic expressed more than once** into one place that both call.
- **Correct the comments:** they say why, not what, and none is out of date.
- **Names say what the thing is** in the project's own words.

## What you report and leave alone

These are the owner's call, so never act on them. List each one in `.intentable/summary.md`, under "For Nate", with where it is:

- a circular dependency or a layering violation;
- code that looks dead;
- a new module or grouping, or moving code across a module or layer boundary.

## Committing

Make at most one commit, "Refactor {{ inputs.change_name }}", and only when the suite passes. If nothing is worth changing, make no commit. That's a good outcome, not a failure.

## Never

- make a merge commit, or pull, rebase or push;
- write a closing keyword followed by an issue reference in a commit message, such as "fixes #3";
- change anything under `.github/` or `.fabro/`, or `bin/publish-spek-page`;
- put an `@` in anything for the issue, except inside backticks for code;
- start subagents or background tasks;
- leave anything uncommitted: if a refactoring doesn't pass, discard it (`git restore --staged --worktree .` and `git clean -fd`), and end with a clean working tree.

Never ask and wait for an answer: nobody is waiting on this run. If you're unsure whether a change is behaviour-preserving, leave it out, and note it under "For Nate".

Add your findings to the end of `.intentable/summary.md`, and change nothing else under `.intentable/`. Stop only once the working tree is clean.
