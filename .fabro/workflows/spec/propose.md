You are writing a request for the New England Music Project website up as an OpenSpec proposal. The site is a Django app that lists music venues, shows and acts in the Northeast US. The repository is checked out in your working directory, and the `openspec` command is installed.

Take the OpenSpec propose stance. Write planning artifacts only, never code, grounded in what the site's code actually does. Read the models, views, templates and management commands the request would touch before you write. Follow `openspec/config.yaml` and the "Specs and tests (OpenSpec)" section of `AGENTS.md`. Keep host and network names out of every OpenSpec file: no machine names, internal addresses or anything secret, since the proposal will be published.

## The issue

- Number: {{ inputs.issue_number }}
- Opened by: {{ inputs.issue_author }}
- Title: {{ inputs.issue_title }}

Body:

```
{{ inputs.issue_body }}
```

Comments so far, oldest first, as JSON (`[{author, body}]`):

```
{{ inputs.issue_thread }}
```

A comment that ends with `<!-- intentable-bridge -->` was posted by the intentable bridge under the `natea` account: an earlier question or summary from this process, or a status note. It is not the owner speaking. The thread is the record of what the person who asked has decided.

## What to do

First decide whether the issue is clear enough to write up.

**If it is**, create one OpenSpec change for it:

1. Choose a new change name: lowercase letters, digits and single hyphens, at most 60 characters, such as `add-venue-hours`. It must not already exist in `openspec/changes/` or, without its date, in `openspec/changes/archive/`.
2. Run `openspec new change <name>`, then write every artifact the schema needs, using `openspec instructions <artifact> --change <name> --json` for each: the proposal, the delta specs, the design and the tasks.
3. Record any decision the thread doesn't settle as an open question in the design, never as settled.
4. Every task group that changes behaviour includes tasks for the automated tests of its scenarios, and the design says how each outside service is mocked.
5. Run `openspec validate <name> --strict` until it passes.
6. If the change needs new or changed screens, give it the label `needs-design`. A later step sketches them.

Then write `.intentable/draft.json`, creating the `.intentable` folder:

```json
{"change": "add-venue-hours", "labels": [], "message": "This covers opening hours on each venue page, taken from the venue's own website. It leaves out holiday hours for now."}
```

The message is for the person who asked, who is not a developer: two to four plain sentences saying what the proposal covers, with no code, no file names, no jargon and no @-mentions. `labels` is empty or `["needs-design"]`.

**If it isn't clear enough to write up**, write no change. Write `.intentable/draft.json` with the state `needs-info`, exactly one `clarity:` label from `clarity:1` to `clarity:3`, and a message that asks exactly one question, the one whose answer would help most. Put no other question mark anywhere in the message.

```json
{"state": "needs-info", "labels": ["clarity:3"], "message": "Should opening hours come from each venue's website, or be typed in by hand?"}
```

Write nothing under `.intentable/` except `draft.json`. A later step checks the draft, and the run fails if it breaks these rules.

Don't review the draft yourself: later steps in this workflow check it and have three fresh reviewers read it. Start no subagents and no background tasks, and don't wait on anything. Your session ends when you stop, and anything still running is lost, so stop only once `.intentable/draft.json` is written.
